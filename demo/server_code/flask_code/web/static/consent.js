let url_prefix = "http://127.0.0.1:5000/"

function makeRandomId() {
    var text = "";
    var possible =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 8; i++)
      text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

$(document).ready(function () {
    var userId;
    var taskOrder;

    $('#agree').click(function() {
        if (window.localStorage.getItem("userId") === null) {
            initialize_localStorage();
        } else {
            load_LocalStorage();
            console.log(localStorage.getItem("userId"))
        }
    
        function initialize_localStorage() {
            // window.localStorage.setItem("intilized", 1); 
            userId = makeRandomId(); // make a userID - TODO replace with call to server to also do sudocu or sbert. i.e. server call to 1) get id and 2) assign either SuDocu or SBERT first
            window.localStorage.setItem("userId", userId);
        }
    
        function load_LocalStorage() {
            userId = window.localStorage.getItem("userId");
        }

        taskOrder = Math.floor(Math.random() * 2)
        localStorage.setItem("taskOrder", taskOrder)

        location.href = './preStudy'
    });
    
    

    
})