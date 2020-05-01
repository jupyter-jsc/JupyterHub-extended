from setuptools import setup

setup(
    name='JupyterHub-extended',
    version='1.1',
    description='Extension for JupyterHub. Used for Jupyter@JSC.',
    author='Tim Kreuzer',
    author_email='jupyter.jsc@fz-juelich.de',
    packages=['j4j_proxy', 'j4j_authenticator', 'j4j_handler', 'j4j_spawner'],
    install_requires=['jupyterhub>=1.1.0', 'oauthenticator==0.8.2', 'pyjwt>=1.7.1']
)
