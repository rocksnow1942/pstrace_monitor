# PSTrace Monitor GUI
[![python version](https://img.shields.io\/badge/python-3.5%20%7C%203.6%20%7C%203.7%20-blue)][pythonwebsite]
### For monitor pstrace files with pstrace 5.7
<!-- *Italic* ; **Bold** ; ***Bold and Italic*** ; ~~Scratch~~ -->
<!-- ### List items -->
<!-- 1. First ordered list item -->
<!-- * Unordered list can use asterisks -->
* The `pstrace_local` monitor save data as mongodb data package in a local json file. 
* The `pstracemonitor_new` monitor upload data to plojo server. 


[pythonwebsite]: https://www.python.org/downloads/release/python-375


### PS trainer 

Use PS trainer to download and view the data downloaded from the reader.

* How to install 
    
    Install Python3.7
    
    Install pip3

    Make a venv with python3.7: `python -m venv venv`

    Activate venv: `source venv/bin/activate` or `./venv/Scripts/activate`

    Install all the packages in requirements.txt by    `pip install -r requirements.txt`

* Run the GUI with `python traner.py`

    If you find any package is missing or some error importing packages, try uninstall the package and reinstall.

* Another GUI is `python app.py`

    This another GUI that we use to work with Pico and PSTrace. Also, it can export data to a csv file or JSON file.