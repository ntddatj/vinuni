import os

def test_frontend_directory_exists():
    assert os.path.isdir("frontend"), "frontend directory does not exist"

def test_package_json_exists():
    assert os.path.isfile(os.path.join("frontend", "package.json")), "package.json does not exist in frontend"

def test_vite_config_exists():
    assert os.path.isfile(os.path.join("frontend", "vite.config.ts")), "vite.config.ts does not exist in frontend"

def test_prettier_config_exists():
    assert os.path.isfile(os.path.join("frontend", ".prettierrc")), ".prettierrc does not exist in frontend"
