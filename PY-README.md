# Instructions for setting up Python Backend for Chatbot

## Requirements
- conda
- pip
- python-3.11

## Setup instructions
1. Clone the repository from the link: [https://github.com/VinitraMk/UAVLogViewer.git](https://github.com/VinitraMk/UAVLogViewer.git)
2. cd into the project directory and activate conda using the command: `conda load module/latest`
3. complete the set node setup for the application per the instructions in README.md file.
3. setup the conda environment using the `environment.yml` file at root repository using the command `conda env create -f environment.yml`.
4. cd into the folder py-backend and create a file config.json
5. Create an openAI account to get free api key. This is done because the code right now uses openAI wrapper to call the together AI api. This gives you the flexibility to also use gpt-4 model in the openAI wrapper in file main.py. Store this key in config.json under the string "OPENAI_API_KEY"
6. Create an account on Google AI studio, to get free tier api key. This is to use the gemini model to handle larger data such as trajectory data of the UAV telemetry logs. Save this key in config.json under the string "GOOGLE_API_KEY"
7. This step is optional. With the openAI key, you can set model to be used as gpt-4 in line 35 of `main.py`. But if you want to use free tier of together AI api, create a together API account to get the free api key. Save this key in config.json under the key "TOGETHER_API_KEY"
8. It is assumed that the frontend application already has access to the cesium api with your cesium api key.
9. Run npm dev command to start the frontend and cd into the py-backend directory and run the command `uvicorn main:app --reload` to start the backend web server powered by FastAPI.
10. Proceed to the browser, access http://localhost:8000 which should serving the vue application. Open up/download the sample vlog, and click on the chat icon far right of the application window. Start chatting with the agent and ask it queries regarding the telemetry data.

Sample query screenshots testing the chatbot

<p float="left">
  <img src="./src/assets/images/chatbot-examples/ss1.png" width="45%" />
  <img src="./src/assets/images/chatbot-examples/ss2.png" width="45%" />
</p>

<p float="left">
  <img src="./src/assets/images/chatbot-examples/ss3.png" width="45%" />
  <img src="./src/assets/images/chatbot-examples/ss4.png" width="45%" />
</p>

