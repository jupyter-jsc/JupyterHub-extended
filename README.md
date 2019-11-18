# JupyterHub extension for Jupyter@JSC

## J4J_Authenticator
Generic [OAuthentitactor](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html) for JupyterHub.
Class to login user with [Unity-IdM](https://www.unity-idm.eu). 
Contains functions to update the memory state from the database. 


## J4J_Spawner
Generic [Spawner](https://jupyterhub.readthedocs.io/en/stable/reference/spawners.html) for JupyterHub.
Users can choose different options for their JupyterLab.

## J4J_Proxy
Custom [Proxy](https://jupyterhub.readthedocs.io/en/stable/reference/proxy.html) for JupyterHub.
Does not trust it's own memory, trust the database instead. 

## J4J_Handler
### API_cancel
Cancel spawning JupyterLab via JupyterHub REST API.

### API_Proxy
Add routes to the proxy via JupyterHub REST API.

### API_Status
Update JupyterLab Status via REST API. Therefore spawner.poll_interval can be -1.

### API_Token
Get OAuth access token, if correct JupyterHub token is granted.

### Home
Update memory state for the user that called the function. Therefore multiple instances of JupyterHub can be started behind one proxy.

### Spawn
Setup proxy routes to the correct instance of JupyterHub. 
