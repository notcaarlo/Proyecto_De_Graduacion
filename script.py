import os
import shutil
from pathlib import Path

def copiar_imagenes(base_dir, output_dir):
    """
    Copia las imágenes individuales a la carpeta de salida.

    :param base_dir: Carpeta donde están las imágenes originales (abiertos o cerrados).
    :param output_dir: Carpeta de salida donde se guardarán las imágenes.
    """
    # Crear la carpeta de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener todas las imágenes de la carpeta base
    imagenes = [f for f in Path(base_dir).glob('*.png')]  # Cambia el formato si es otro tipo de imagen

    # Ordenar las imágenes (asegúrate que los nombres de las imágenes estén en el orden correcto)
    imagenes.sort()  # Si las imágenes están numeradas o en orden adecuado

    # Copiar las imágenes a la carpeta de salida
    for img in imagenes:
        shutil.copy(img, output_dir)

# Definir las rutas de entrada y salida para 'abiertos' y 'cerrados'
base_dir_abiertos = "C:/Users/DELL/Downloads/train/Open_Eyes"  # Ruta donde están las imágenes 'abiertos'
output_dir_abiertos = "data/somnolencia/abiertos"  # Ruta de salida para las imágenes 'abiertos'

base_dir_cerrados = "C:/Users/DELL/Downloads/train/Closed_Eyes"  # Ruta donde están las imágenes 'cerrados'
output_dir_cerrados = "data/somnolencia/cerrados"  # Ruta de salida para las imágenes 'cerrados'

# Llamar a la función para copiar las imágenes en las carpetas 'abiertos' y 'cerrados'
copiar_imagenes(base_dir_abiertos, output_dir_abiertos)
copiar_imagenes(base_dir_cerrados, output_dir_cerrados)

print(f"Imágenes copiadas a {output_dir_abiertos} y {output_dir_cerrados}")