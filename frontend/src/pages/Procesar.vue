<template>
  <div class="container-process pt-4 sm:ml-64">
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-xl md:text-2xl font-semibold text-gray-600 mb-6 pb-4">
        PROCESAMIENTO DE DOCUMENTOS
      </h1>

      <div v-if="!processed" class="bg-white rounded-lg shadow-sm p-6 mb-8">
        <h2 class="text-lg font-medium text-gray-600 mb-4">
          AÑADIR NUEVOS DOCUMENTOS
        </h2>

        <div
          class="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center text-center bg-gray-50"
          @drop.prevent="handleDrop"
          @dragover.prevent
        >
          <p class="text-gray-500 mb-4">Arrastre archivos aquí o ...</p>

          <input
            ref="fileInput"
            type="file"
            class="hidden"
            @change="handleFileChange"
            accept=".pdf"
            :disabled="fileSelected"
          />

          <button
            class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-6 rounded-md transition duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
            @click="selectFile"
            :disabled="fileSelected || processing"
          >
            Seleccionar archivos
          </button>

          <div v-if="loading" class="w-full mt-6">
            <div class="w-full bg-gray-200 rounded-full h-4">
              <div
                class="bg-blue-500 h-4 rounded-full transition-all duration-300"
                :style="{ width: progress + '%' }"
              ></div>
            </div>
            <p class="text-blue-500 mt-2">Cargando archivo...</p>
          </div>

          <div v-if="fileName" class="mt-4 text-gray-700">
            Archivo seleccionado: <strong>{{ fileName }}</strong>
          </div>

          <button
            v-if="fileSelected && !processing && !processed && !loading"
            class="mt-4 bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-6 rounded-md transition duration-300"
            @click="iniciarProcesamiento"
          >
            Procesar
          </button>

          <div id="spinner" style="display: none">
            <!-- Puedes usar un simple SVG o cualquier otro contenido -->
            <svg
              class="animate-spin h-8 w-8 text-blue-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              ></path>
            </svg>
            <span>Esperando resultado...</span>
          </div>


        </div>
        <p class="text-gray-500 mt-4 text-sm md:text-base text-center">
          Formatos soportados : PDF
        </p>
      </div>

      <!-- <div v-if="processed && mdStatus !== 'done'" class="w-full mt-6">
        <div class="w-full bg-gray-200 rounded-full h-4">
          <div
            class="bg-green-500 h-4 rounded-full transition-all duration-300"
            :style="{ width: mdProgress + '%' }"
          ></div>
        </div>
        <p class="text-green-500 mt-2">Procesando... {{ mdProgress }}%</p>
      </div> -->

      <div v-if="processed" class="bg-white rounded-lg shadow-sm p-6">
        <div class="text-center">
          <p class="text-gray-600 font-medium mb-4">¡Documento procesado!</p>
          <span class="text-blue-700 font-semibold"
            >procesado-{{ fileName }}</span
          ><br />
          <button
            @click="handleDescargarMarkdown"
            class="inline-flex items-center justify-center bg-green-500 hover:bg-green-600 text-white font-medium py-3 px-6 rounded-md transition duration-300 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 mt-4"
            style="margin-left: 10px"
          >
            <span class="mr-2 text-blue-200">
              <img
                src="../assets/descargar.png"
                alt="download-icon"
                class="w-8 h-8"
              />
            </span>
            <span class="text-center">Descargar</span>
          </button>
        </div>

        <!-- Procesar un nuevo documento -->
        <div class="mt-6 border-t-1 border-gray-200 pt-2">
          <button
            class="bg-white hover:bg-gray-200 text-gray-800 font-medium py-2 px-4 rounded transition duration-200"
            @click="resetProcess"
          >
            Procesar otro PDF
          </button>
        </div>
        <!-- ----------- -->
      </div>

      <!-- show urls extracted -->
      <div v-if="processed" class="bg-white rounded-lg shadow-sm p-6 mt-6">
        <div v-if="estado.urls && estado.urls.length">
          <h3 class="text-lg font-semibold text-gray-700 mb-3">
            URLs extraídas:
          </h3>
          <ul class="list-disc list-inside space-y-1">
            <li
              v-for="(url, idx) in estado.urls"
              :key="idx"
              class="text-blue-700 hover:underline break-all"
            >
              <a :href="url" target="_blank" rel="noopener noreferrer">{{
                url
              }}</a>
            </li>
          </ul>
        </div>
        <div v-else>
          <pre
            class="bg-gray-100 rounded p-4 text-sm text-gray-700 overflow-x-auto"
            >{{ estado }}</pre
          >
        </div>
      </div>
      
      <!-- show error message -->
      <div v-if="estado && estado.status === 'error'" class="mt-4 text-red-700">
        {{ estado.message }}
      </div>

      <!-- codigo de testeo -->
      <!-- <div v-if="estado && estado.message" class="mt-4 text-blue-700">
        {{ estado.message }} <br />
        <button
          @click="consultarEstado"
          class="ml-4 bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-md transition duration-300"
        >
          Consultar Estado
        </button>
      </div> -->
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import {
  procesar_pdf,
  descargarMarkdown,
  obtenerUrlsExtraidas,
  upload_pdf_with_progress,
  obtenerResultadoPdf,
} from "../api"; // importing modules from API.js

//reactives variables
const prompt = ref("simple");
const batchSize = ref(3);
const pauseSeconds = ref(30);
const estado = ref("");
const fileInput = ref(null);
const fileName = ref("");
const fileSelected = ref(false);
const loading = ref(false);
const processing = ref(false);
const processed = ref(false);
const progress = ref(0);
const mdProgress = ref(0);
const mdStatus = ref("processing");
let ws = null;

/**
 * File upload event
 * @param {Event} event - The file input change event
 * @returns {Promise<void>}
 */
async function handleFileChange(event) {
  const file = event.target.files[0];
  if (file && file.type === "application/pdf") {
    // validate name of file
    if (nameFileValidate(file.name) === false) {
      alert(
        "⚠️ El nombre del archivo no es válido, deber seguir el formato: ddmmyyyy  ( ejemplo:22042025 ) "
      );
      return;
    }

    loading.value = true;
    progress.value = 0;
    try {
      const res = await upload_pdf_with_progress(file, (percent) => {
        progress.value = percent;
      });
      fileName.value = res.filename;
      fileSelected.value = true;
    } catch {
      // Manejo de error
    } finally {
      loading.value = false;
    }
  } else {
    alert("Solo se permiten archivos PDF.");
  }
}

/**
 * Function to process the PDF
 * @param {Object} params - Parameters for processing
 * @returns {Promise<void>}
 */
async function iniciarProcesamiento() {
  processing.value = true;
  iniciarConsultaResultado(fileName.value); //iniciar spinner
  try {
    const resultado = await procesar_pdf({
      filename: fileName.value,
      prompt: prompt.value,
      batchSize: batchSize.value,
      pauseSeconds: pauseSeconds.value,
    });
    estado.value = resultado;
    // Obtenr las URLs extraídas despues de procesar el PDF
    const urls = await obtenerUrlsExtraidas(
      fileName.value.replace(/\.pdf$/i, "")
    );
    estado.value.urls = urls;
    processed.value = true;
  } catch {
    estado.value = { status: "error", message: "Error al procesar el PDF" };
  }
  processing.value = false;
}

/**
 * Function to download the processed markdown file
 * @returns {Promise<void>}
 */
async function handleDescargarMarkdown() {
  const blob = await descargarMarkdown(fileName.value.replace(/\.pdf$/i, ""));
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `procesado-${fileName.value.replace(/\.pdf$/i, "")}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Function to get upload file using drag and drop
 * @param {DragEvent} event - The drag event
 * @returns {Promise<void>}
 */
async function handleDrop(event) {
  const file = event.dataTransfer.files[0];
  if (file && file.type === "application/pdf") {
    // validate name of file
    if (nameFileValidate(file.name) === false) {
      alert(
        "⚠️ El nombre del archivo no es válido, deber seguir el formato: ddmmyyyy  ( ejemplo:22042025 ) "
      );
      return;
    }
    loading.value = true;
    progress.value = 0;
    try {
      const res = await upload_pdf_with_progress(file, (percent) => {
        progress.value = percent;
      });
      fileName.value = res.filename;
      fileSelected.value = true;
    } catch (err) {
      alert("Error al subir el archivo PDF. Intenta nuevamente.");
      fileName.value = "";
      fileSelected.value = false;
    } finally {
      loading.value = false;
    }
  } else {
    alert("Solo se permiten archivos PDF.");
  }
}

/**
 * Function to get the status of the process
 * @returns {Promise<void>}
 */
async function consultarEstado() {
  estado.value = await obtenerEstado();
}

/**
 * Function to select the file
 */
function selectFile() {
  if (!fileSelected.value) fileInput.value.click();
}

/**
 * Function to reset the process
 */
function resetProcess() {
  fileName.value = "";
  fileSelected.value = false;
  loading.value = false;
  processing.value = false;
  processed.value = false;
  progress.value = 0;
  downloadUrl.value = "";
}

/**
 * Function to validate the file name
 * @param {string} name - The file name
 * @returns {boolean} - True if valid, false otherwise
 */
function nameFileValidate(name) {
  const match = name.match(/^(\d{2})(\d{2})(\d{4})\.pdf$/i);
  if (!match) {
    return false;
  }
  return true;
}

/*
 * Function to get the result of the PDF
 * @param {string} filename - The name of the file
 * @param {number} delayMs - The delay in milliseconds
 * @param {number} maxIntentos - The maximum number of attempts
 * @returns {Promise<string>} - The result of the PDF
 */
async function esperarResultadoPdf(filename, delayMs = 15000, maxIntentos = 48) {
  showSpinner(); // comenzar a mostrar el spinner
  let intentos = 0;
  try {
    while (intentos < maxIntentos) {
      try {
        const resultado = await obtenerResultadoPdf(filename);
        return resultado; // Resultado obtenido, se sale del bucle
      } catch (err) {
        console.log("Esperando resultado...", err.message);
        await new Promise(resolve => setTimeout(resolve, delayMs));
        intentos++;
      }
    }
    throw new Error("Tiempo de espera agotado para obtener el resultado del PDF");
  } finally {
    hideSpinner(); // Asegura que el spinner se oculte en cualquier caso
  }
}

function showSpinner() {
  const spinner = document.getElementById("spinner");
  if (spinner) {
    spinner.style.display = "flex"; // O 'block', según tu diseño
  }
}

function hideSpinner() {
  const spinner = document.getElementById("spinner");
  if (spinner) {
    spinner.style.display = "none";
  }
}

async function iniciarConsultaResultado(fileName) {
  try {
    const resultado = await esperarResultadoPdf(fileName.value); // reemplaza "ejemplo" por el nombre base del PDF
    console.log("Resultado obtenido:", resultado);
    // Aquí puedes actualizar el DOM o notificar al usuario con el resultado
  } catch (error) {
    console.error("Error:", error.message);
  }
}

</script>
