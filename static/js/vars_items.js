function modific_element_advisor(data){
    var text_area_item_html = `
        <style>

            .item_advisor {
                border-radius: 10px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                transition: 0.3s;
            }
            .item:hover {
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
            }
            .header_txt_area {
                padding: 10px;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                background-image: linear-gradient(to right, #7b4397, #dc2430);
                color: white;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            .text-area {
                padding: 20px;
                font-size: 18px;
            }
            
        </style>

        <div class="container_text_area">
            <div class="item_advisor">
                <div class="header_txt_area">` + data.deploy_item.title + `</div>
                <center><h4>-- ` + data.deploy_item.sub_title + ` --</h4></center>
                <div class="text-area">
                <div class="chat-message user" style=>
                <h3>  ` + data.deploy_item.text_area_placeholder + `</h3>
            </div>
            </div>
        </div>
        `;
return text_area_item_html;
}
function alert_advisor(data){
    var area_item_html = `
    <style>
    .item_advisor {
        border-radius: 10px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        transition: 0.3s;
    }
    .item:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    .header_txt_area {
        padding: 10px;
        font-family: Arial, Helvetica, sans-serif;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        background-image: linear-gradient(to right, #f80b0b, #884448);
        color: white;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
      }
    .text-area {
        padding: 20px;
        font-size: 18px;
    }
    .btn {
        display: inline-block;
        padding: 15px 25px;
        font-size: 24px;
        cursor: pointer;
        text-align: center; 
        box-shadow: 0px 3px 10px rgba(0, 0, 0, 0.2);
        text-decoration: none;
        outline: none;
        color: #fff;
        background-color: #4CAF50;
        border: none;
        border-radius: 15px;
        box-shadow: 0 9px #999;
    }

    .btn:hover {background-color: #3e8e41}

    .btn:active {
      background-color: #3e8e41;
      box-shadow: 0px 3px 10px rgba(0, 0, 0, 0.2);
      box-shadow: 0 5px #666;
      transform: translateY(4px);
    }
    
    .gray-btn {
      background-image: linear-gradient(to right, #a1a1a1, #d3d3d3);
    }
    
    .red-btn {
      background-image: linear-gradient(to right, #f80b0b, #884448);
    }
</style>

<div class="container_text_area">
    <div class="item_advisor">
        <div class="header_txt_area">` + data.deploy_item.title + `</div>
        <center><h4>-- ` + data.deploy_item.sub_title + ` --</h4></center>
        <div class="text-area">
            <button id="continue_doc"  onclick="sendPostRequest('/message');" class="btn gray-btn">Continuar haciendo el documento</button>
            <button id="cancel_doc" onclick="sendPostRequest('/cancel_document');" class="btn red-btn">Estoy seguro/a, cancelar el documento</button>
        </div>
    </div>
</div>

    `;   

return area_item_html;
}
function document_download_div(data){
    var document_download_item = `
        <style>

            .item_advisor {
                border-radius: 10px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                transition: 0.3s;
            }
            .item:hover {
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
            }
            .header_txt_area {
                padding: 10px;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                background-image: linear-gradient(to right, #7b4397, #dc2430);
                color: white;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            .text-area {
                padding: 20px;
                font-size: 18px;
            }
            
        </style>

        <div class="container_text_area">
            <div class="item_advisor">
                <div class="header_txt_area">` + data.deploy_item.title + `</div>
                <center><h4>-- De click en el boton para descargar el documento. --</h4></center>

                <div class="text-area">
                <div class="chat-message user" style=>
                <h3>  </h3>
                <a href="` + data.deploy_item.parameters.uri_doc + `" onclick="sendPostRequest('/message');" style="text-decoration: none; color:white"><div class="recordButton">Descargar Documento</div></a>
            </div>
            </div>
        </div>
        `;
return document_download_item;
}