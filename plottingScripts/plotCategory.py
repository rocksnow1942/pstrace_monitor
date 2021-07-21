import pandas as pd
import seaborn as sns


"""
plot category scatter plot from data in a table.

Step 1:
generate a csv file like this: (first row is categorical label)
   VS	 VINS	  VNS	Copy
0.268	0.241	0.167	300
0.250	0.261	0.204	300
0.247	0.223	0.185	300
0.278	0.201	0.209	300
0.172	0.250	0.086	100
0.189	0.190	0.170	100
0.232	0.281	0.220	100
0.250	0.248	0.174	100

Step 2: change parameters below then run script.
To save figure, uncomment the f.savefig() line.

"""



file = r"C:\Users\hui\Desktop\data.csv"


df = pd.read_csv(file)
 
var_name = 'Method'
value_name = 'CT'


# this melt is to turn column name to variable name
df = df.melt(id_vars=('Copy',),var_name=var_name, value_name = value_name)

# kind can be box, violin, boxen, point, bar, swarm, strip
f = sns.catplot(x=var_name,y=value_name,data=df,kind='swarm',hue='Copy', height=3,aspect=1.2)

f.fig.axes[0].set_title(value_name)

 
# f.savefig('tosave.svg')





