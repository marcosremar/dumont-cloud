# Dumont Machine Switcher

VS Code extension for switching between GPU machines in Dumont Cloud.

## Features

- **Status Bar Button**: Shows current machine with GPU name and status
- **Quick Picker**: Fast machine selection with Ctrl+Shift+P > "Dumont: Switch Machine"
- **Machine Status**: Visual indicators for online/offline machines
- **Auto Refresh**: Machines list updates every 30 seconds
- **Start Machines**: Start offline machines directly from VS Code

## Configuration

The extension can be configured via:

1. **Environment Variables** (recommended for code-server):
   - `DUMONT_API_URL`: Dumont Cloud API URL
   - `DUMONT_AUTH_TOKEN`: JWT authentication token
   - `DUMONT_MACHINE_ID`: Current machine ID

2. **Config File** (`~/.dumont/config.json`):
   ```json
   {
     "api_url": "http://your-dumont-server:5000",
     "auth_token": "your-jwt-token"
   }
   ```

3. **VS Code Settings**:
   - `dumont.apiUrl`: API URL
   - `dumont.authToken`: Auth token
   - `dumont.currentMachineId`: Current machine ID

## Usage

1. Click the GPU icon in the status bar (bottom right)
2. Or use Command Palette: `Ctrl+Shift+P` > "Dumont: Switch Machine"
3. Select a machine from the list
4. If the machine is offline, you'll be prompted to start it

## Building

```bash
npm install
npm run compile
npm run package
```

This will create a `.vsix` file that can be installed in VS Code/code-server.
