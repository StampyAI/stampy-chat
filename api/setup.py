from setuptools import setup, find_packages

setup(
    name='Stampy-chat',
    version='0.1',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        'flask',
        'gunicorn',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'werkzeug',
        'flask-cors',
        'openai',
        'numpy',
        'tenacity',
        'tiktoken',
        'pinecone-client',
        'python-dotenv',
        'discord-webhook',
        'requests'
    ],
)
