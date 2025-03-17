import PyInstaller.__main__
import os
import sys

# Define command line arguments for PyInstaller
args = [
    'app.py',                       # Your main script
    '--name=AI_Vision_Snipping',    # Name of the exe
    '--onefile',                    # Create a single exe file
    '--windowed',                   # Don't open a console window
    '--add-data=.env;.',            # Include the .env file
    '--clean',                      # Clean cached data before building
]

# Only add icon if it exists
icon_path = 'icon.ico'
if os.path.exists(icon_path):
    args.append(f'--icon={icon_path}')
else:
    print(f"Warning: Icon file '{icon_path}' not found. Building without custom icon.")

# Run PyInstaller with the arguments
print("Building executable with PyInstaller...")
PyInstaller.__main__.run(args)

print("Build completed! Check the dist folder for your executable.") 