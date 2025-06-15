from bs4 import BeautifulSoup
import re

def format_expression(plot):
    msgformat = "[a-zA-Z][a-zA-Z0-9_]+\.[a-zA-Z0-9_]+"
    msg = re.findall(msgformat, plot)
    if len(msg) == 0:
        return ""
    function = plot.replace(msg[0], "a").replace(":2", "")
    if "sqrt" in plot or "lowpass" in plot:
        return ""
    if len(function) > 1:
        return "        ['" + msg[0] + "', 0, undefined, function(a) { return " + function + " } ]," 
    else:
        return "        ['" + msg[0] + "', 0],"   

with open("mavgraphs.xml") as f:
    bs = BeautifulSoup(f, "lxml")
    for graph in bs.find_all("graph"):
        #print(graph)
        
        counter = 0
        for expression in graph.find_all("expression"):
            print("'"+graph["name"]+ " "*counter + "':")
            counter += 1
            print("    [")
            # this includes a hack to remove repeated spaces: https://stackoverflow.com/questions/1546226/simple-way-to-remove-multiple-spaces-in-a-string
            for plot in " ".join(expression.text.replace("\n", "").strip().split()).split(" "): 
                print(format_expression(plot))
            print("    ],")



