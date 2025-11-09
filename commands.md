# 1. Crear venv
python -m venv venv

# 2. Activar venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest-xprocess

# 4. Ejecutar tests
gltest

# 5. Desactivar (cuando termines)
deactivate# 1. Crear venv
python -m venv venv

# 2. Activar venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest-xprocess

# 4. Ejecutar tests
gltest

# 5. Desactivar (cuando termines)
deactivate