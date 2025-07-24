from setuptools import setup, find_packages

setup(
    name="teamcity_monitor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "requests",
        "python-dotenv",
        "pymysql"
    ],
    python_requires=">=3.8",
) 