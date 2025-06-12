from langchain_experimental.utilities import PythonREPL

with open("python_code.py", "r") as f:
    python_code = f.read()

python_repl = PythonREPL()

ans = python_repl.run(python_code)
print("--"* 20)
print(ans)
print("--"* 20)