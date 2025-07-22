from setuptools import setup, find_packages

setup(
    name="teamcity_monitor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "fastapi",
        "requests",
        "python-dotenv",
        "pydantic"
    ],
    python_requires=">=3.8",
) 