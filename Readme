# Network Flow Visualizer & Editor

A toolset for architecting and visualizing neural network architectures through a GUI editor and py5 rendering engine.

## Components

- **`visual_editor.py`**: PyQt6 GUI for editing layers, groups, and hyperparameters
- **`visual_torch.py`**: py5 rendering engine for network visualization

## ⚠️ Critical Setup Requirements

### JVM Directory Configuration

**MUST** configure the JVM directory before running:

In `visual_torch.py`, set the `java_home_path` variable to your JDK/JRE installation:

```python
java_home_path = r"C:\path\to\your\jvm"
```

**Common JVM locations:**
- Windows: `C:\Program Files\Java\jdk-xx\bin\server`
- Windows: `C:\Program Files\Java\jre-xx\bin\server`
- macOS: `/Library/Java/JavaVirtualMachines/jdk-xx.jdk/Contents/Home/lib/server`

**To find your JVM directory:**
```bash
# Windows
where java

# macOS/Linux
which java
```
Then navigate to the `bin/server` subdirectory of that Java installation.

### py5 Import and Directory Issues

**Problem**: py5 may fail to import if the JVM directory is not correctly specified or if PATH environment variables are missing.

**Solutions:**

1. **Set JAVA_HOME environment variable:**
   ```bash
   # Windows (PowerShell)
   $env:JAVA_HOME = "C:\Program Files\Java\jdk-xx"
   $env:PATH += ";$env:JAVA_HOME\bin"

   # macOS/Linux
   export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-xx.jdk/Contents/Home
   export PATH=$JAVA_HOME/bin:$PATH
   ```

2. **Alternative: Use py5's auto-detection:**
   If the above fails, py5 can sometimes auto-detect the JVM. Remove the `java_home_path` setting and let py5 search, though this is less reliable.

3. **Verify py5 installation:**
   ```bash
   pip install --upgrade py5
   python -c "import py5; print(py5.__version__)"
   ```

## Installation

```bash
pip install PyQt6 py5
```

## Usage

1. **Launch editor:**
   ```bash
   python visual_editor.py
   ```

2. **Edit network:**
   - **Double-click** values to edit parameters
   - **Right-click** layers: Duplicate, Rename, Delete, or Add New Group
   - **Right-click** groups: Duplicate, Add Attribute, or Delete
   - **Right-click** blank area: Add New Layer
   - **Drag** layers to reorder the network flow

3. **File operations:**
   - **📁 Load JSON**: Import existing network configuration
   - **📄 Export JSON**: Save current configuration to file
   - **🔄 Reset to Original**: Revert to default template

4. **Visualize:**
   - Click **"🚀 Inject Parameters & Preview Render"** to generate visualization