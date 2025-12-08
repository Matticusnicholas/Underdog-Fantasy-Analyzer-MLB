from setuptools import setup, find_packages

setup(
    name="underdog-fantasy-analyzer",
    version="1.0.0",
    description="MLB Best Ball Fantasy Analyzer with Screenshot OCR Parser",
    author="Fantasy Analyzer Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pytesseract>=0.3.10",
        "Pillow>=10.0.0",
        "opencv-python>=4.8.0",
        "sqlalchemy>=2.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "tabulate>=0.9.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fantasy-analyzer=analyzer.cli:main",
        ],
    },
    python_requires=">=3.9",
)
