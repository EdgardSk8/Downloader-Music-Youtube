document.addEventListener("DOMContentLoaded", () => {

    // ------------------------------------------------------------------
    // Referencias al DOM (los nombres deben coincidir con index.html)
    // ------------------------------------------------------------------
    const BtnBuscarCancion = document.querySelector(".Btn-Buscar-Cancion");
    const BtnPegar = document.querySelector(".Btn-Pegar");
    const input = document.querySelector("#youtube-url");

    const loadingDiv = document.querySelector(".loading");
    const previewDiv = document.querySelector("#Informacion-Cancion");

    const titulo = document.querySelector(".Titulo-Cancion");
    const informacion = document.querySelector(".Informacion-Cancion-p");
    const imagen = document.querySelector(".Imagen-Caratula");

    const renameInput = document.querySelector("#rename-title");
    const btnDescargar = document.querySelector(".Btn-Descargar-Cancion");
    const avisoCola = document.querySelector("#Aviso-Cola");

    const listaDescargas = document.querySelector("#Lista-Descargas");
    const descargasVacias = document.querySelector("#Descargas-Vacias");
    const contadorDescargas = document.querySelector("#Contador-Descargas");
    const btnAbrirCarpeta = document.querySelector("#btn-abrir-carpeta");

    // Imagen de respaldo servida por Flask (antes se usaba /downloader.png, que no existe)
    const ImagenVacia = "/static/sinimagen.png";

    let videoActual = null;   // Datos del video buscado (para la vista previa)
    let avisoTimeout = null;  // Temporizador del aviso "Añadido a la cola"

    // Último estado visto de cada tarea: detecta el cambio a "descargado" para animarlo
    const estadosPrevios = new Map();

    // Vista del panel: detallada (progreso y detalles) o compacta (nombre + icono)
    const radiosVista = document.querySelectorAll('input[name="vista-descargas"]');
    let vistaCompacta = false;

    // Sondeo adaptativo: 100 ms mientras hay descargas en curso, 800 ms en reposo
    const INTERVALO_ACTIVO = 100;
    const INTERVALO_REPOSO = 800;

    let temporizadorDescargas = null;
    let consultaEnCurso = false;
    let hayDescargasActivas = false;
    let firmaEstructura = "";
    let ultimosDatos = null;   // Última respuesta de /descargas (repintados locales)
    let peticionActual = 0;    // Descarta respuestas viejas si hay peticiones solapadas

    // Nodos de cada tarjeta que se refrescan en sitio (sin repintar toda la lista)
    const itemsDescarga = new Map();

    // ------------------------------------------------------------------
    // Vista previa
    // ------------------------------------------------------------------
    async function obtenerInfo(url) {
        const respuesta = await fetch("/informacion", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url })
        });

        const datos = await respuesta.json();

        if (!respuesta.ok) {
            throw datos;
        }

        return datos;
    }

    function limpiarNombre(texto) {
        return (texto || "")
            .replace(/[<>:"/\\|?*]+/g, "") // Caracteres inválidos en nombres de archivo de Windows
            .replace(/^[#\s]+/, "")        // Títulos tipo "## Canción" → "Canción"
            .trim();
    }

    function nombrePropuesto(videoInfo) {
        const titulo = limpiarNombre(videoInfo.title || "cancion");

        // Regla: si el título NO tiene guion, se antepone "Autor - "
        if (!titulo.includes("-")) {
            const autor = limpiarNombre(videoInfo.uploader || "")
                .replace(/\s*-\s*topic$/i, "") // Canales automáticos "Artista - Topic"
                .trim();

            if (autor) return `${autor} - ${titulo}`;
        }

        // Si ya tiene guion, se respeta: la izquierda es el autor y la derecha el título
        return titulo;
    }

    function mostrarPreview(videoInfo) {
        videoActual = videoInfo;

        titulo.textContent = videoInfo.title;

        // textContent evita inyectar HTML con datos que vienen de YouTube
        informacion.textContent =
            `Duración: ${formatearDuracion(videoInfo.duration)}` +
            ` · Autor: ${videoInfo.uploader || "--"}`;

        // Si la miniatura falla, se usa la imagen local una sola vez (sin bucle)
        imagen.onerror = () => {
            imagen.onerror = null;
            imagen.src = ImagenVacia;
        };
        imagen.src = videoInfo.thumbnail || ImagenVacia;

        renameInput.value = nombrePropuesto(videoInfo);
        renameInput.disabled = false;
        btnDescargar.disabled = false;

        previewDiv.classList.remove("d-none");
    }

    function formatearDuracion(segundos) {
        const total = Number(segundos) || 0;
        const horas = Math.floor(total / 3600);
        const minutos = Math.floor((total % 3600) / 60);
        const segs = Math.floor(total % 60);

        if (horas > 0) {
            return `${horas}:${minutos.toString().padStart(2, "0")}:${segs.toString().padStart(2, "0")}`;
        }

        return `${minutos}:${segs.toString().padStart(2, "0")}`;
    }

    // ------------------------------------------------------------------
    // Cola de descargas
    // ------------------------------------------------------------------
    async function encolarDescarga(url, customTitle, uploader) {
        const respuesta = await fetch("/descargar", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                url,
                custom_title: customTitle,
                uploader // Respaldo del backend si yt-dlp no trae el autor al descargar
            })
        });

        const datos = await respuesta.json();

        if (!respuesta.ok) {
            throw datos;
        }

        return datos;
    }

    async function actualizarDescargas(forzar = false) {
        // Sondeo adaptativo: así cualquier ventana refleja las descargas aunque se hayan
        // iniciado en otra, y con algo en curso la barra se refresca cada 100 ms.
        if (consultaEnCurso && !forzar) return;

        consultaEnCurso = true;
        const peticion = ++peticionActual;

        try {
            const respuesta = await fetch("/descargas");

            if (!respuesta.ok || peticion !== peticionActual) return;

            const datos = await respuesta.json();

            if (peticion !== peticionActual) return;

            ultimosDatos = datos;
            hayDescargasActivas = datos.activas.length > 0 || datos.cola.length > 0;

            const firma = firmaEstructuraDe(datos);

            if (!forzar && firma === firmaEstructura) {
                // Misma lista: solo cambian %/velocidad/ETA → se actualiza en sitio
                actualizarTareasEnCurso(datos);
            } else {
                firmaEstructura = firma;
                renderizarDescargas(datos);
            }

        } catch (error) {
            console.error("No se pudo actualizar la lista de descargas:", error);

        } finally {
            if (peticion === peticionActual) {
                consultaEnCurso = false;
                programarActualizacion();
            }
        }
    }

    function programarActualizacion() {
        clearTimeout(temporizadorDescargas);

        temporizadorDescargas = setTimeout(
            actualizarDescargas,
            hayDescargasActivas ? INTERVALO_ACTIVO : INTERVALO_REPOSO
        );
    }

    function firmaEstructuraDe(datos) {
        // Todo lo que cambia la FORMA de la lista (no el progreso en vivo)
        return JSON.stringify([
            datos.activas.map((t) => [t.id, t.estado]),
            datos.cola.map((t) => [t.id, t.estado, t.posicion]),
            datos.historial.map((t) => [t.id, t.estado]),
        ]);
    }

    function actualizarTareasEnCurso(datos) {
        for (const tarea of [...datos.activas, ...datos.cola]) {
            const refs = itemsDescarga.get(tarea.id);
            if (!refs) continue;

            if (refs.badge) {
                refs.badge.textContent = textoEstado(tarea);
                refs.badge.className =
                    "Descarga-Badge badge flex-shrink-0 " + claseBadge(tarea.estado);
            }

            if (refs.barra) {
                refs.barra.style.width = `${tarea.estado === "procesando"
                    ? 100
                    : Math.min(100, Number(tarea.porcentaje) || 0)}%`;
            }

            if (refs.detalleIzquierda) {
                refs.detalleIzquierda.textContent = detalleIzquierda(tarea);
                refs.detalleIzquierda.title = refs.detalleIzquierda.textContent;
            }

            if (refs.detalleDerecha) {
                refs.detalleDerecha.textContent = detalleDerecha(tarea);
            }

            if (refs.icono) {
                actualizarIconoEstado(refs.icono, tarea);
            }
        }
    }

    function renderizarDescargas(datos) {
        listaDescargas.innerHTML = "";
        itemsDescarga.clear();

        const grupos = [
            ["En curso", datos.activas],
            ["En cola", datos.cola],
            ["Historial", datos.historial]
        ];

        const recienCompletadas = new Set();
        const items = new Map();

        for (const [tituloGrupo, tareas] of grupos) {
            if (!tareas.length) continue;

            const cabeceraGrupo = document.createElement("div");
            cabeceraGrupo.className = "d-flex align-items-center justify-content-between mt-2 mb-1";

            const etiqueta = document.createElement("p");
            etiqueta.className = "Descarga-Grupo text-uppercase text-secondary fw-semibold mb-0";
            etiqueta.textContent = tituloGrupo;
            cabeceraGrupo.appendChild(etiqueta);

            if (tituloGrupo === "Historial") {
                const btnLimpiar = document.createElement("button");
                btnLimpiar.type = "button";
                btnLimpiar.className = "Descarga-Limpiar";
                btnLimpiar.textContent = "Limpiar todo";
                btnLimpiar.title = "Quitar todo el historial (los archivos NO se borran)";
                btnLimpiar.addEventListener("click", limpiarHistorial);
                cabeceraGrupo.appendChild(btnLimpiar);
            }

            listaDescargas.appendChild(cabeceraGrupo);

            for (const tarea of tareas) {
                // Solo se anima la transición a "descargado" (no el historial al abrir la app)
                const completadaAhora =
                    tarea.estado === "descargado" &&
                    estadosPrevios.has(tarea.id) &&
                    estadosPrevios.get(tarea.id) !== "descargado";

                if (completadaAhora) recienCompletadas.add(tarea.id);

                const item = crearItemDescarga(tarea, completadaAhora);
                items.set(tarea.id, item);
                listaDescargas.appendChild(item);
                registrarRefsDescarga(tarea, item);
            }
        }

        // Estado actual = referencia para el siguiente sondeo
        for (const tarea of [...datos.activas, ...datos.cola, ...datos.historial]) {
            estadosPrevios.set(tarea.id, tarea.estado);
        }

        const pendientes = datos.activas.length + datos.cola.length;

        contadorDescargas.textContent =
            pendientes === 1 ? "1 pendiente" : `${pendientes} pendientes`;

        contadorDescargas.className = "badge " + (
            pendientes
                ? "bg-success-subtle text-success-emphasis"
                : "bg-secondary-subtle text-secondary-emphasis"
        );

        const hayTareas = listaDescargas.children.length > 0;

        // Con tareas se ve la lista; sin tareas el aviso ocupa todo el ancho (texto sin apretar)
        listaDescargas.classList.toggle("d-none", !hayTareas);
        descargasVacias.style.display = hayTareas ? "none" : "";

        // Animación tipo Chrome: el badge vuela hasta el botón de la carpeta
        for (const id of recienCompletadas) {
            animarDescargaCompletada(items.get(id));
        }
    }

    function crearItemDescarga(tarea, completadaAhora = false) {
        const terminada = tarea.estado === "descargado" || tarea.estado === "error";

        const nombre = document.createElement("span");
        nombre.className = "Descarga-Nombre text-truncate";
        nombre.textContent = tarea.custom_title || tarea.nombre_archivo || "Canción";
        nombre.title = nombre.textContent;

        // --- Vista compacta: solo "Autor - Título" + icono (✔ / ✖) ---
        if (vistaCompacta) {
            const item = document.createElement("div");
            item.className = "Descarga-Item Descarga-Item-Compacta border rounded-3 px-2 py-1 mb-1 d-flex align-items-center gap-1";
            if (completadaAhora) item.classList.add("Descarga-Completada");

            item.append(nombre, crearIconoEstado(tarea));
            if (terminada) item.append(crearBotonEliminar(tarea));

            return item;
        }

        // --- Vista detallada ---
        const item = document.createElement("div");
        item.className = "Descarga-Item border rounded-3 p-2 mb-2";
        if (completadaAhora) item.classList.add("Descarga-Completada");

        // Fila superior: nombre de la canción + botón para quitarla del historial
        const cabecera = document.createElement("div");
        cabecera.className = "Descarga-Cabecera";
        cabecera.append(nombre);
        if (terminada) cabecera.append(crearBotonEliminar(tarea));

        const badge = document.createElement("span");
        badge.className = "Descarga-Badge badge flex-shrink-0 " + claseBadge(tarea.estado);
        badge.textContent = textoEstado(tarea);

        const estado = document.createElement("div");
        estado.className = "Descarga-Estado";
        estado.append(badge);

        // Barra de progreso (5 px)
        const progreso = document.createElement("div");
        progreso.className = "progress mt-2";
        progreso.style.height = "5px";

        const barra = document.createElement("div");
        barra.className = "progress-bar " + claseBarra(tarea.estado);
        barra.style.width = `${tarea.estado === "procesando"
            ? 100
            : Math.min(100, Number(tarea.porcentaje) || 0)}%`;
        progreso.appendChild(barra);

        // Fila inferior: detalle a la izquierda, dato extra a la derecha
        const detalle = document.createElement("div");
        detalle.className = "Descarga-Detalle d-flex flex-wrap justify-content-between gap-2 text-secondary mt-1";

        const izquierda = document.createElement("span");
        izquierda.className = "Descarga-Detalle-Izquierda text-truncate";
        izquierda.textContent = detalleIzquierda(tarea);
        izquierda.title = izquierda.textContent;

        const derecha = document.createElement("span");
        derecha.className = "Descarga-Detalle-Derecha flex-shrink-0";
        derecha.textContent = detalleDerecha(tarea);

        detalle.append(izquierda, derecha);

        item.append(cabecera, estado, progreso, detalle);
        return item;
    }

    function registrarRefsDescarga(tarea, item) {
        // Se guardan los nodos que cambian con el progreso para actualizarlos en sitio
        itemsDescarga.set(tarea.id, {
            badge: item.querySelector(".Descarga-Badge"),
            barra: item.querySelector(".progress-bar"),
            icono: item.querySelector(".Descarga-Icono"),
            detalleIzquierda: item.querySelector(".Descarga-Detalle-Izquierda"),
            detalleDerecha: item.querySelector(".Descarga-Detalle-Derecha"),
        });
    }

    function actualizarIconoEstado(icono, tarea) {
        icono.className = "Descarga-Icono flex-shrink-0";

        switch (tarea.estado) {
            case "descargado":
                icono.textContent = "✔";
                icono.classList.add("text-success");
                icono.title = "Descargado";
                break;
            case "error":
                icono.textContent = "✖";
                icono.classList.add("text-danger");
                icono.title = tarea.error || "Error";
                break;
            case "descargando":
            case "procesando":
                icono.textContent = `${Math.floor(Number(tarea.porcentaje) || 0)}%`;
                icono.classList.add("text-success");
                icono.title = textoEstado(tarea);
                break;
            default:
                icono.textContent = tarea.posicion ? `#${tarea.posicion}` : "…";
                icono.classList.add("text-secondary");
                icono.title = "En cola";
        }
    }

    function crearIconoEstado(tarea) {
        const icono = document.createElement("span");
        actualizarIconoEstado(icono, tarea);
        return icono;
    }

    function crearBotonEliminar(tarea) {
        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "Descarga-Eliminar flex-shrink-0";
        boton.textContent = "×";
        boton.title = "Quitar del historial (no borra el archivo)";
        boton.setAttribute("aria-label", "Quitar del historial");
        boton.addEventListener("click", () => quitarDelHistorial(tarea.id));
        return boton;
    }

    function textoEstado(tarea) {
        switch (tarea.estado) {
            case "descargando":
                return `Descargando ${Math.floor(Number(tarea.porcentaje) || 0)}%`;
            case "procesando":
                return "Procesando";
            case "descargado":
                return "Descargado ✔";
            case "error":
                return "Error";
            default:
                return "En cola";
        }
    }

    function claseBadge(estado) {
        switch (estado) {
            case "descargando":
            case "descargado":
                return "bg-success";
            case "procesando":
                return "bg-warning text-dark";
            case "error":
                return "bg-danger";
            default:
                return "bg-secondary"; // En cola
        }
    }

    function claseBarra(estado) {
        switch (estado) {
            case "error":
                return "bg-danger";
            case "procesando":
                // Rayas animadas: la conversión no tiene % medible, pero se ve que avanza
                return "bg-warning progress-bar-striped progress-bar-animated";
            default:
                return "bg-success";
        }
    }

    function detalleIzquierda(tarea) {
        switch (tarea.estado) {
            case "descargando": {
                const porcentaje = Math.floor(Number(tarea.porcentaje) || 0);
                const velocidad = tarea.speed ? `${formatearBytes(tarea.speed)}/s` : "...";
                return `${porcentaje}% · ${velocidad} · ETA ${formatearEta(tarea.eta)}`;
            }
            case "procesando":
                // "Convirtiendo a M4A…", "Incrustando carátula…", etc. (lo manda el backend)
                return tarea.etapa || "Procesando audio…";
            case "descargado":
                return `100% · ${tarea.nombre_archivo || "Archivo guardado"}`;
            case "error":
                return tarea.error || "Ocurrió un error";
            default:
                return "Esperando turno";
        }
    }

    function detalleDerecha(tarea) {
        switch (tarea.estado) {
            case "descargando":
                return `${formatearBytes(tarea.descargado || 0)} / ${formatearBytes(tarea.total || 0)}`;
            case "procesando":
                return "100%";
            case "descargado":
            case "error":
                return formatearHora(tarea.finalizada);
            default:
                return tarea.posicion ? `#${tarea.posicion} en cola` : "";
        }
    }

    function formatearBytes(bytes) {
        const valor = Number(bytes) || 0;
        if (valor <= 0) return "0 B";

        const unidades = ["B", "KB", "MB", "GB"];
        const indice = Math.min(
            unidades.length - 1,
            Math.floor(Math.log(valor) / Math.log(1024))
        );

        return `${(valor / Math.pow(1024, indice)).toFixed(1)} ${unidades[indice]}`;
    }

    function formatearEta(segundos) {
        const valor = Number(segundos) || 0;
        if (valor <= 0) return "--:--";

        const minutos = Math.floor(valor / 60);
        const segs = Math.floor(valor % 60);

        return `${minutos}:${segs.toString().padStart(2, "0")}`;
    }

    function formatearHora(epoch) {
        if (!epoch) return "";

        // Formato de 12 horas (10:41 AM / 10:41 PM)
        const fecha = new Date(epoch * 1000);
        const horas24 = fecha.getHours();
        const horas12 = horas24 % 12 || 12;
        const minutos = fecha.getMinutes().toString().padStart(2, "0");
        const sufijo = horas24 < 12 ? "AM" : "PM";

        return `${horas12}:${minutos} ${sufijo}`;
    }

    function formatearFechaHora(fechaIso) {
        // Fecha completa + hora 12 h con segundos (para el modal de versiones)
        const fecha = new Date(fechaIso);

        if (Number.isNaN(fecha.getTime())) return "";

        const dia = fecha.toLocaleDateString("es", {
            day: "numeric",
            month: "long",
            year: "numeric"
        });

        const horas24 = fecha.getHours();
        const horas12 = horas24 % 12 || 12;
        const minutos = String(fecha.getMinutes()).padStart(2, "0");
        const segundos = String(fecha.getSeconds()).padStart(2, "0");
        const sufijo = horas24 < 12 ? "AM" : "PM";

        return `${dia}, ${horas12}:${minutos}:${segundos} ${sufijo}`;
    }

    // ------------------------------------------------------------------
    // Versiones (parches) — ESCRITO A MANO
    // Al publicar una versión nueva, añade aquí su entrada (arriba del todo).
    // Formato de cada entrada:
    //   { version: "0.0.3", fecha: "2026-11-12T13:00:00-07:00", cambios: ["..."] }
    // "fecha" es ISO 8601 con zona horaria; se muestra en 12 h con segundos.
    // ------------------------------------------------------------------
    const PARCHES = [
        {
            version: "0.1",
            fecha: "2026-11-12T14:22:00-07:00",
            cambios: [
                "Soporte para Linux: la aplicación se abre en el navegador.",
                "Iconos redondos en la web, la aplicación y el navbar.",
                "Aviso si falta FFmpeg o Node en el sistema."
            ]
        },
        {
            version: "0.0.3",
            fecha: "2026-11-12T12:42:47-07:00",
            cambios: [
                "Mejoras de compatibilidad y de la actualización.",
                "Nuevas secciones: términos, versiones e icono de la app."
            ]
        },
        {
            version: "0.0.2",
            fecha: "2026-11-12T12:04:33-07:00",
            cambios: [
                "Mejoras en la actualización automática."
            ]
        },
        {
            version: "0.0.1",
            fecha: "2026-11-12T12:01:42-07:00",
            cambios: [
                "Primera versión publicada."
            ]
        }
    ];

    async function mostrarParches() {
        const contenedor = document.getElementById("Lista-Parches");
        const versionActual = await cargarVersion();

        contenedor.innerHTML = "";

        if (PARCHES.length === 0) {
            const aviso = document.createElement("p");
            aviso.className = "small text-secondary mb-0";
            aviso.textContent = "Todavía no hay versiones publicadas.";
            contenedor.appendChild(aviso);
        }

        for (const parche of PARCHES) {
            const tarjeta = document.createElement("div");
            tarjeta.className = "Parche";

            const fila = document.createElement("div");
            fila.className = "d-flex align-items-center justify-content-between gap-2";

            const titulo = document.createElement("p");
            titulo.className = "fw-semibold mb-0";
            titulo.textContent = `Versión ${parche.version}`;
            fila.appendChild(titulo);

            if (versionActual && parche.version === versionActual) {
                const actual = document.createElement("span");
                actual.className = "badge bg-success";
                actual.textContent = "Actual";
                fila.appendChild(actual);
            }

            const fecha = document.createElement("p");
            fecha.className = "small text-secondary mb-1";
            fecha.textContent = formatearFechaHora(parche.fecha);

            const lista = document.createElement("ul");
            lista.className = "small mb-0 ps-3";

            for (const cambio of parche.cambios || []) {
                const elemento = document.createElement("li");
                elemento.textContent = cambio;
                lista.appendChild(elemento);
            }

            tarjeta.append(fila, fecha, lista);
            contenedor.appendChild(tarjeta);
        }

        if (!modalParches) {
            modalParches = new bootstrap.Modal(
                document.getElementById("modalParches")
            );
        }

        modalParches.show();
    }

    // ------------------------------------------------------------------
    // Historial: quitar una entrada o limpiarlo entero (los archivos NO se borran)
    // ------------------------------------------------------------------
    async function quitarDelHistorial(taskId) {
        try {
            const respuesta = await fetch(
                `/descargas/${encodeURIComponent(taskId)}`,
                { method: "DELETE" }
            );

            if (!respuesta.ok) {
                const datos = await respuesta.json().catch(() => ({}));
                alert(datos.error || "No se pudo quitar del historial.");
                return;
            }

            estadosPrevios.delete(taskId);
            await actualizarDescargas(true);

        } catch (error) {
            console.error("No se pudo quitar del historial:", error);
            alert("No se pudo quitar del historial.");
        }
    }

    async function limpiarHistorial() {
        // Confirmación con modal propio (nada de confirm() nativo)
        if (!modalLimpiar) {
            modalLimpiar = new bootstrap.Modal(
                document.getElementById("modalLimpiar")
            );
        }

        modalLimpiar.show();
    }

    async function confirmarLimpiarHistorial() {
        if (modalLimpiar) modalLimpiar.hide();

        try {
            const respuesta = await fetch("/historial", { method: "DELETE" });

            if (!respuesta.ok) throw new Error("Respuesta no válida");

            estadosPrevios.clear();
            await actualizarDescargas(true);

        } catch (error) {
            console.error("No se pudo limpiar el historial:", error);
            alert("No se pudo limpiar el historial.");
        }
    }

    // ------------------------------------------------------------------
    // Vista de la lista: detallada o compacta (se recuerda en el navegador)
    // ------------------------------------------------------------------
    function aplicarVista(valor) {
        vistaCompacta = valor === "compacta";

        for (const radio of radiosVista) {
            radio.checked = radio.value === valor;
        }

        try {
            localStorage.setItem("vistaDescargas", valor);
        } catch (error) {
            // localStorage puede estar bloqueado: la vista funciona igual en esta pestaña
        }

        // Repintado inmediato con los últimos datos (sin esperar al sondeo)
        if (ultimosDatos) renderizarDescargas(ultimosDatos);
    }

    function restaurarVista() {
        let guardada = null;

        try {
            guardada = localStorage.getItem("vistaDescargas");
        } catch (error) {
            return;
        }

        if (guardada === "compacta" || guardada === "detallada") {
            aplicarVista(guardada);
        }
    }

    // ------------------------------------------------------------------
    // Animación al terminar una descarga (el badge vuela a la carpeta)
    // ------------------------------------------------------------------
    function animarDescargaCompletada(item) {
        if (!item || !item.isConnected) return;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        // En la vista detallada vuela el badge; en la compacta, el icono ✔
        const origenEl =
            item.querySelector(".Descarga-Badge") ||
            item.querySelector(".Descarga-Icono");

        if (!origenEl) return;

        const origen = origenEl.getBoundingClientRect();
        const destino = btnAbrirCarpeta.getBoundingClientRect();
        if (!origen.width || !destino.width) return;

        // Copia del badge que vuela hasta el botón de la carpeta (como en Chrome).
        // Va en <body>: la lista se vuelve a pintar cada 800 ms y si no, se perdería.
        const volador = origenEl.cloneNode(true);
        volador.classList.add("Descarga-Volando");
        volador.style.width = `${origen.width}px`;
        volador.style.height = `${origen.height}px`;
        volador.style.left = `${origen.left}px`;
        volador.style.top = `${origen.top}px`;
        document.body.appendChild(volador);

        const dx = destino.left + destino.width / 2 - (origen.left + origen.width / 2);
        const dy = destino.top + destino.height / 2 - (origen.top + origen.height / 2);
        const arco = Math.min(90, 30 + Math.abs(dy) * 0.2); // Curva hacia arriba en mitad del vuelo

        const vuelo = volador.animate([
            { transform: "translate(0, 0) scale(1)", opacity: 1 },
            {
                transform: `translate(${dx * 0.5}px, ${dy * 0.5 - arco}px) scale(0.8)`,
                opacity: 1,
                offset: 0.55
            },
            { transform: `translate(${dx}px, ${dy}px) scale(0.1)`, opacity: 0 }
        ], {
            duration: 750,
            easing: "cubic-bezier(0.3, 0, 0.2, 1)"
        });

        vuelo.onfinish = () => {
            volador.remove();
            pulsarCarpeta();
        };
    }

    function pulsarCarpeta() {
        // Quitar y volver a poner la clase reinicia la animación si ya estaba activa
        btnAbrirCarpeta.classList.remove("Carpeta-Pulso");
        void btnAbrirCarpeta.offsetWidth;
        btnAbrirCarpeta.classList.add("Carpeta-Pulso");
    }

    // ------------------------------------------------------------------
    // Utilidades de interfaz
    // ------------------------------------------------------------------
    function toggleLoading(show) {
        loadingDiv.style.visibility = show ? "visible" : "hidden";
    }

    function mostrarAviso(texto) {
        avisoCola.textContent = texto;
        avisoCola.style.visibility = "visible";

        clearTimeout(avisoTimeout);
        avisoTimeout = setTimeout(() => {
            avisoCola.style.visibility = "hidden";
        }, 2500);
    }

    // Aviso persistente (Bootstrap Toast) para problemas de configuración del sistema
    function mostrarToastError(texto) {
        if (!window.bootstrap) {
            console.warn(texto);
            return;
        }

        const contenedor = document.createElement("div");
        contenedor.className = "toast-container position-fixed bottom-0 end-0 p-3";
        contenedor.style.zIndex = "1090";

        const toast = document.createElement("div");
        toast.className = "toast align-items-center text-bg-danger border-0";
        toast.setAttribute("role", "alert");
        toast.setAttribute("aria-live", "assertive");

        const fila = document.createElement("div");
        fila.className = "d-flex";

        const cuerpo = document.createElement("div");
        cuerpo.className = "toast-body";
        cuerpo.textContent = texto;

        const cerrar = document.createElement("button");
        cerrar.type = "button";
        cerrar.className = "btn-close btn-close-white me-2 m-auto";
        cerrar.setAttribute("data-bs-dismiss", "toast");
        cerrar.setAttribute("aria-label", "Cerrar");

        fila.append(cuerpo, cerrar);
        toast.append(fila);
        contenedor.append(toast);
        document.body.append(contenedor);

        toast.addEventListener("hidden.bs.toast", () => contenedor.remove());
        new bootstrap.Toast(toast, { autohide: false }).show(); // Se cierra solo con la X
    }

    // En Linux FFmpeg y Node no vienen incluidos (como en el instalador de Windows)
    async function revisarHerramientas() {
        try {
            const respuesta = await fetch("/diagnostico");
            if (!respuesta.ok) return;

            const datos = await respuesta.json();

            if (!datos.ffmpeg) {
                mostrarToastError(
                    "Falta FFmpeg: sin él no se puede convertir a M4A. " +
                    "Instálalo (sudo apt install ffmpeg) o colócalo junto a la aplicación."
                );
            } else if (!datos.node) {
                mostrarToastError(
                    "Falta Node.js: algunos vídeos de YouTube lo necesitan. " +
                    "Instálalo (sudo apt install nodejs) o colócalo junto a la aplicación."
                );
            }
        } catch (error) {
            // Servidor antiguo o sin conexión: no se avisa
        }
    }

    function limpiarFormulario() {
        // Deja la vista lista para pegar la siguiente canción
        videoActual = null;

        input.value = "";
        renameInput.value = "";
        renameInput.disabled = true;
        btnDescargar.disabled = true;

        imagen.src = ImagenVacia;
        previewDiv.classList.add("d-none");

        input.focus();
    }

    // ------------------------------------------------------------------
    // Eventos
    // ------------------------------------------------------------------
    BtnBuscarCancion.addEventListener("click", async () => {
        const url = input.value.trim();

        if (!url) {
            alert("Por favor pega un enlace de YouTube.");
            return;
        }

        toggleLoading(true);

        try {
            const videoInfo = await obtenerInfo(url);
            mostrarPreview(videoInfo);
        } catch (error) {
            alert(
                "Error al obtener información: " +
                (error.error || error)
            );
        } finally {
            toggleLoading(false);
        }
    });

    BtnPegar.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();

            if (text) {
                input.value = text.trim();
            } else {
                alert("El portapapeles está vacío.");
            }

        } catch (error) {
            alert("No se pudo acceder al portapapeles.");
            console.error(error);
        }
    });

    btnDescargar.addEventListener("click", async () => {
        if (!videoActual) return;

        const customTitle = renameInput.value.trim() || videoActual.title;

        btnDescargar.disabled = true;

        try {
            const autor = videoActual.uploader || videoActual.channel || "";

            await encolarDescarga(input.value.trim(), customTitle, autor);
            mostrarAviso("Añadido a la cola ✔");
            limpiarFormulario(); // Limpia URL y nombre para la siguiente canción
            await actualizarDescargas();
        } catch (error) {
            // Si falla, se deja todo como estaba para poder reintentar
            alert("Error al añadir a la cola: " + (error.error || error));
            btnDescargar.disabled = false;
        }
    });

    btnAbrirCarpeta.addEventListener("click", async () => {
        try {
            const respuesta = await fetch("/abrir-carpeta", { method: "POST" });
            const datos = await respuesta.json();

            if (!respuesta.ok) {
                alert(datos.error || "No se pudo abrir la carpeta.");
            }
        } catch (error) {
            console.error("No se pudo abrir la carpeta:", error);
            alert("No se pudo abrir la carpeta.");
        }
    });

    // ------------------------------------------------------------------
    // Versión y actualización automática
    // ------------------------------------------------------------------
    async function cargarVersion() {
        try {
            const respuesta = await fetch("/version");
            const datos = await respuesta.json();

            document.getElementById("version-app").textContent = `v${datos.version}`;

            return datos.version;

        } catch (error) {
            console.error("No se pudo obtener la versión:", error);
            return null;
        }
    }

    async function cargarCarpeta() {
        // Muestra la ruta real en el tooltip del botón de carpeta
        try {
            const respuesta = await fetch("/carpeta");
            const datos = await respuesta.json();

            if (datos.carpeta) {
                btnAbrirCarpeta.title = `Abrir carpeta de descargas\n${datos.carpeta}`;
            }
        } catch (error) {
            console.error("No se pudo obtener la carpeta:", error);
        }
    }

    function compararVersiones(actual, nueva) {
        // Acepta "v1.0.1", "1.0.1-beta", "1.0.1+build"; compara por tramos numéricos
        const normalizar = (version) =>
            String(version || "")
                .trim()
                .replace(/^v/i, "")
                .split("-")[0]
                .split("+")[0];

        const versionActual = normalizar(actual).split(".").map((n) => Number(n) || 0);
        const versionNueva = normalizar(nueva).split(".").map((n) => Number(n) || 0);

        for (let i = 0; i < Math.max(versionActual.length, versionNueva.length); i++) {
            const actualNumero = versionActual[i] || 0;
            const nuevaNumero = versionNueva[i] || 0;

            if (nuevaNumero > actualNumero) return true;
            if (nuevaNumero < actualNumero) return false;
        }

        return false;
    }

    let modalActualizacion = null;
    let modalTerminos = null;
    let modalParches = null;
    let modalLimpiar = null;
    let avisoActualizacionMostrado = false;

    async function comprobarActualizacion() {
        try {
            const respuesta = await fetch("/actualizacion");

            if (!respuesta.ok) return;

            const datos = await respuesta.json();
            const versionActual = await cargarVersion();

            if (!versionActual || !datos.version) return;
            if (!compararVersiones(versionActual, datos.version)) return;
            if (avisoActualizacionMostrado) return; // Mostrarlo una vez por sesión

            avisoActualizacionMostrado = true;

            document.getElementById("version-nueva").textContent =
                `Versión ${datos.version} (tienes la ${versionActual})`;

            document.getElementById("mensaje-actualizacion").textContent =
                datos.mensaje || "Nueva versión disponible.";

            document.getElementById("btn-actualizar").onclick =
                () => iniciarActualizacion(datos);

            if (!modalActualizacion) {
                modalActualizacion = new bootstrap.Modal(
                    document.getElementById("modalActualizacion")
                );
            }

            modalActualizacion.show();

        } catch (error) {
            console.error(
                "No se pudo comprobar si existe una actualización:",
                error
            );
        }
    }

    async function iniciarActualizacion(datos) {
        const boton = document.getElementById("btn-actualizar");
        const progreso = document.getElementById("progreso-actualizacion");
        const barra = document.getElementById("barra-actualizacion");
        const estado = document.getElementById("estado-actualizacion");
        const cerrar = document.querySelector("#modalActualizacion .btn-close");
        const despues = document.querySelector("#modalActualizacion .btn-light");

        if (!datos.url) {
            alert("La actualización no tiene una URL de descarga válida.");
            return;
        }

        boton.disabled = true;
        boton.textContent = "Descargando…";

        // Mientras se instala, no se puede cerrar el modal por accidente
        if (cerrar) cerrar.disabled = true;
        if (despues) despues.disabled = true;

        progreso.classList.remove("d-none");
        estado.classList.remove("d-none");
        estado.textContent = "Descargando la nueva versión…";
        barra.style.width = "0%";

        try {
            const respuesta = await fetch("/actualizar", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    url: datos.url,
                    version: datos.version,
                    tamano: datos.tamano || 0
                })
            });

            const resultado = await respuesta.json();

            if (!respuesta.ok) {
                throw new Error(
                    resultado.error || "No se pudo iniciar la actualización."
                );
            }

            vigilarActualizacion();

        } catch (error) {
            boton.disabled = false;
            boton.textContent = "Reintentar";
            if (cerrar) cerrar.disabled = false;
            if (despues) despues.disabled = false;
            progreso.classList.add("d-none");
            estado.classList.add("d-none");
            alert("No se pudo actualizar: " + error.message);
        }
    }

    async function vigilarActualizacion() {
        const boton = document.getElementById("btn-actualizar");
        const progreso = document.getElementById("progreso-actualizacion");
        const barra = document.getElementById("barra-actualizacion");
        const estado = document.getElementById("estado-actualizacion");

        try {
            const respuesta = await fetch("/actualizar/progreso");

            if (respuesta.ok) {
                const datos = await respuesta.json();

                barra.style.width =
                    `${Math.min(100, Number(datos.porcentaje) || 0)}%`;

                if (datos.estado === "lista") {
                    barra.style.width = "100%";
                    estado.textContent = "Descargada. Reiniciando la aplicación…";
                    boton.textContent = "Reiniciando…";
                    return;
                }

                if (datos.estado === "error") {
                    boton.disabled = false;
                    boton.textContent = "Reintentar";
                    progreso.classList.add("d-none");
                    estado.classList.add("d-none");
                    alert(
                        "No se pudo actualizar: " +
                        (datos.error || "error desconocido")
                    );
                    return;
                }

                estado.textContent = datos.total
                    ? `Descargando… ${Math.floor(datos.porcentaje)}% ` +
                      `(${formatearBytes(datos.descargado)} de ${formatearBytes(datos.total)})`
                    : `Descargando… ${formatearBytes(datos.descargado)}`;
            }

        } catch (error) {
            // La app puede estar cerrándose para aplicar la actualización
        }

        setTimeout(vigilarActualizacion, 300);
    }

    // ------------------------------------------------------------------
    // Arranque
    // ------------------------------------------------------------------
    // ------------------------------------------------------------------
    // Icono ⓘ: regla del nombre (se cierra con la X o pulsando fuera)
    // ------------------------------------------------------------------
    const btnReglaNombre = document.querySelector("#btn-regla-nombre");
    let popoverRegla = null;

    if (window.bootstrap && btnReglaNombre) {
        popoverRegla = new bootstrap.Popover(btnReglaNombre, {
            trigger: "manual", // Lo abrimos/cerramos nosotros para controlar la X y el clic fuera
            placement: "bottom",
            html: true,
            sanitize: false,   // El contenido es fijo del propio código (no viene del usuario)
            container: "body", // Evita que lo recorte el contenedor
            title: "¿Cómo nombrar la canción?",
            content: `
                <button type="button" class="btn-close regla-cerrar"
                    style="position: absolute; top: .45rem; right: .45rem;"
                    aria-label="Cerrar"></button>
                <p class="mb-1">Formato: <strong>Autor - Título</strong></p>
                <p class="mb-1 text-secondary">Ejemplo: <em>Los Ángeles Azules - Mis Sentimientos</em></p>
                <p class="mb-0 text-secondary">Sin guion, el autor se agrega solo.</p>
            `,
        });

        btnReglaNombre.addEventListener("click", () => popoverRegla.toggle());

        document.addEventListener("click", (evento) => {
            if (!popoverRegla) return;

            if (evento.target.closest(".regla-cerrar")) {
                popoverRegla.hide();
                return;
            }

            if (evento.target.closest(".popover")) return;          // Clic dentro del recuadro
            if (evento.target.closest("#btn-regla-nombre")) return; // El icono ya hace toggle

            popoverRegla.hide(); // Clic fuera del recuadro: se cierra
        });
    }

    // Footer: términos y versiones; confirmación de limpieza con modal propio
    document.getElementById("btn-terminos").addEventListener("click", () => {
        if (!modalTerminos) {
            modalTerminos = new bootstrap.Modal(
                document.getElementById("modalTerminos")
            );
        }

        modalTerminos.show();
    });

    document.getElementById("btn-parches").addEventListener("click", mostrarParches);
    document.getElementById("btn-confirmar-limpiar").addEventListener("click", confirmarLimpiarHistorial);

    cargarVersion();
    cargarCarpeta();
    comprobarActualizacion();
    revisarHerramientas();

    // Vista de descargas: guarda la elección y repinta la lista al cambiarla
    for (const radio of radiosVista) {
        radio.addEventListener("change", () => {
            if (radio.checked) aplicarVista(radio.value);
        });
    }

    restaurarVista();

    // Sondeo adaptativo: 100 ms con algo en curso (barra fluida) y 800 ms en reposo.
    // actualizarDescargas() se reprograma sola en cada respuesta.
    actualizarDescargas();
});