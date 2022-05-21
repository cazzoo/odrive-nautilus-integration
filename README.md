# odrive-nautilus-integration
This is a nautilus-python plugin for odrive.

It requires that you have odrive (bin client) available in the system.
You may think add the odrive folder containing the bin in your path.

Also, it requires that you have the odriveagent running.

This is current very early stages of the nautilus integration.

# TODO, IDEAS, MISSING FEATURES: 
- handing user settings (using simple configparser lib from python).
- Manage syncstate of all selected files (currently only the 1st item selected is checked).
- Add new window forms to handle missing operation (settings, actions).
- Enabling multi-threading capabilities so not to lock nautilus in cas of long running action (sync).
- Prompt to download odrive client/agent if missing.

# About
This project is **active** so feel free to submit PR for enhancements.
I am open to any suggestions, so please do not make an active fork from this project.