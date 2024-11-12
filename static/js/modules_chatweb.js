function verify_res_server(data_res) {
    let serverMessage = document.createElement("div");
  
    switch (data_res.role) {
      case "server":
        let message_render;
        if (data_res.message === "Error_Interpreter_modific_element") {
            current_interaction = null;
            message_render = "Disculpame, fue mi error no interprete bien lo que dijiste, mejor continuemos haciendo el documento que te parece ?";
        } else {
            const textArea = document.createElement('textarea');
            textArea.innerHTML = data_res.message;
            message_render = textArea.value;
        }
        serverMessage.classList.add("chat-message", "server");    
        serverMessage.innerHTML = message_render;
        const chatMessagesContainer = document.getElementById("chat-messages");
        if (chatMessagesContainer) {
            chatMessagesContainer.appendChild(serverMessage);
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
        } else {
            console.error("Element with ID 'chat-messages' not found!");
        }
        return false;
  
      case "user":
        const userIndex = parseInt(data_res.user_index); // Parse user index to a number
        if (userIndex >= 1 && userIndex) {
            serverMessage.classList.add("chat-message", "user");
            const randomColor = `hsl(${userIndex * 210}, 100%, 70%)`; // Adjust hue for different color variations
            serverMessage.style.backgroundColor = randomColor;
            const textArea = document.createElement('textarea');
            textArea.innerHTML = data_res.message;
            const unescapedHTML = textArea.value;
            serverMessage.innerHTML = unescapedHTML;
            const chatMessagesContainer = document.getElementById("chat-messages");
            if (chatMessagesContainer) {
                chatMessagesContainer.appendChild(serverMessage);
                chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
            } else {
                console.error("Element with ID 'chat-messages' not found!");
            }
        } else {
            console.error("Invalid user index:", userIndex);
        }
        return false;
  
      case "deploy_item":
        return data_res.message !== undefined ? data_res.message : false;
  
      default:
        return false;
    }
  }
  
  async function updateMessageHistory() {
    const sessionHash = "{{hashchat}}"; // Replace with the actual value of the session hash
    
    const requestData = {
      hashsesion: sessionHash,
      len_list_history: list_history.length
    };
  
    const requestOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    };
  
    try {
      const response = await fetch('/update_messages_history', requestOptions);
      const responseData = await response.json();
      let is_deploy_item;
      if (response.ok) {
        if (responseData.message === "not_update_history_chat") {
          return 0;
        } else if (Array.isArray(responseData)) {
          ChatMessagesContainer.innerHTML="";
          list_history = responseData;
          for (const message of responseData) {
            is_deploy_item = verify_res_server(message);
            if (is_deploy_item) {
              updateUIForDeployment(true);
              updatePreviewContent(is_deploy_item);
            } else {
              updateUIForDeployment(false);
            }
          }
        } else if (responseData.messages && Array.isArray(responseData.messages)) {
          list_history = responseData;
          ChatMessagesContainer.innerHTML = "";
          const messageList = responseData.messages;
          for (const message of messageList) {
            is_deploy_item = verify_res_server(message);
            if (is_deploy_item) {
              updateUIForDeployment(true);
              updatePreviewContent(is_deploy_item);
            } else {
              updateUIForDeployment(false);
            }
          }
        } else {
          console.error('Unexpected response format. Messages are not in an array.');
        }
      } else {
        console.error('Error updating message history:', responseData.error);
      }
    } catch (error) {
      console.error('Unexpected error updating message history:', error);
    }
  }
  