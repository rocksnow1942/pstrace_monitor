import requests

try:
    url = "https://raw.githubusercontent.com/rocksnow1942/ngs_server/master/app/tasks/pstrace_monitor.py"
    plot = "https://raw.githubusercontent.com/rocksnow1942/ngs_server/master/app/tasks/pstrace_plot.py"
    res = requests.get(url)
    res2 = requests.get(plot)
    print (res2.text)

    with open('./pstracemonitor.py' ,'wt') as f:
        f.write(res.text)
    with open('./pstraceplot.py' ,'wt' ) as f:
        f.write(res2.text)
except Exception as e:
    print(e)
    input('Error caught, Enter to contiue.')
