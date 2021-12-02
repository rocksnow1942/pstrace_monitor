1.           According to the attached ppt, the specific functional requirements and computing power requirements are 
not so clear to us at this moment. Is it possible for your side to provide us a sample and instruction manual? We would like to evaluate it’s operation. 

A: See attached code.

2.           Based on our understanding, the software needs to be rewritten based on the new MCU selected, right?
A: Right.
3.           What does the web server created in the MCU have to show? What are the requirements for the web interface? 
What kind of control has to be done on that page? If the web page is complicated, the MCU can not be able to handle.

A: Currently, the web server simply hosts static web app files. (There are no http API requests) 
The static web app is written with javascript and react and compiled to a website of a few MBs 
(The app is a work in progress. currently it's 3MB, but as we add more stuff it might grow). The 
interactivity of the page is done through websocket communication between the browser and the 
reader.The core function of the webpage is display reader status and control reader. These functions 
all have very small data packet size, the speed requirement is also low.Some of the functions it 
supports now:

1. display the reader status (the data packet for this would be very small, but 
relatively frequent, every few seconds.)

2. Some controls: wifi connectivity: connect reader 
to the wifi network by providing the wifi password. reader factory reset.

3. Display history results. The results are just positive or negative, we can paginate as well. So not much.

4. Some other simple interactivity like, users enter their username and password etc. We don't have a complete software design yet, so these are subject to changes.We can add/delete certain functions depending on the MCU capability and our needs.

4.           When mcu is a hot spot to connect other devices in the LAN, how many devices can connect at the same time? If too many, the MCU may not be able to support.

A: We don't need to support too many. I would imagine 3 is good enough. 

5.           What is the sampling rate of the data? For example, the duration between two samplings.

The measurement is done every 20 seconds. At each measurement, 2-4 channels are read. 
For each channel, 120 data points are collected over a course of ~ 1-2 seconds. The data is sent back from the ADuCM355 chip. 
I think it is possible to migrate some data processing code to the ADuCM355 to leverage its Arm CPU. 
So that the ADuCM355 can send the processed data to save the MCU processing power and the UART bandwidth. 

6.           The original data curve fitting is to carry out what kind of curve fitting? Are there any other calculations? This is related to the evaluation of the computational power of the MCU.

A: You can evaluate the attached code for the sample data processing pipeline. Please note: this is our current data process pipeline. It has the potential to be greatly simplified. We can discuss if the process looks daunting.

7.           The analysis results are to be stored in a SQlite database. Is this database stored on a separate server? 

A: The database is on Raspberry Pi. We are using this database to store all the raw data as well, 
this is totally unnecessary in the future. We only need to store a positive / negative result and some QC parameters in the future. 


Overall, the firmware is the way it is right now due to 
    1 ). our R&D nature in the beginning and a lot of functions are unnecessary for production; 
    2 ). we are greatly leveraging the power of RaspberryPi and convenience of python scientific calculation packages; so many functions are not designed in an efficient way that is important for a resource limited MCU.