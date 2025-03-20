const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

// Define the backend path (located in the "backend" folder)
const backendPath = path.join(__dirname, 'backend', 'backend.py');

let mainWindow;
let pythonProcess;

console.log("Electron process architecture:", process.arch);

// Function to start the Python backend
function startPythonBackend() {
    console.log("Starting Python backend...");
    const pythonPath = '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3';
    
    pythonProcess = spawn(pythonPath, ['-u', backendPath], {
        cwd: __dirname,
        stdio: 'pipe'
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python stdout: ${data.toString()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python stderr: ${data.toString()}`);
    });
}

// Create the Electron window and start backend
app.on('ready', () => {
    startPythonBackend();

    mainWindow = new BrowserWindow({
        width: 1400,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false  // Only during development! Remove in production
        },
    });

    mainWindow.loadFile('index.html');
    mainWindow.webContents.openDevTools();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
});

// Stop the backend when the app quits
app.on('quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});
