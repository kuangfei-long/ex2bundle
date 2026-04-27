import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-app.js";
import { getDatabase, ref, set, get, query, onValue, child } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-database.js";

var x = 0;
var userId = localStorage.getItem("userId");

const firebaseConfig = {
    apiKey: "AIzaSyDLVqj7ehZhAPXydgsvDWLJD7luKFBkKFg",
    authDomain: "sudocu-fc487.firebaseapp.com",
    databaseURL: "https://sudocu-fc487-default-rtdb.firebaseio.com",
    projectId: "sudocu-fc487",
    storageBucket: "sudocu-fc487.appspot.com",
    messagingSenderId: "110827457299",
    appId: "1:110827457299:web:6023fd1d7a1a33b5e228e6",
    measurementId: "G-SSMTJZCHS1"
};

const app = initializeApp(firebaseConfig);

// Get a reference to the database service
const db = getDatabase(app);

// write answer to firebase database
function writeUserData(db, userId, question, answer) {
    set(ref(db, 'users/' + userId + '/preStudy/' + question), {
      answer : answer
    });
}

// validate answers. 
//If checkValidity is false or no answer is given, an info circle and feedback message is provided to let the user know his answer is invalid.
function validate_form(formId, feedbackId, feedbackMessage) {
    var value = "";
    document.getElementById(feedbackId).innerHTML = "";
    value = $("#" + formId).val();
    if (document.getElementById(formId).checkValidity() === false || value.toString().length === 0) {
        document.getElementById(feedbackId).innerHTML = '<i class="fa fa-info-circle" style="color:red"></i>' +
        "\xa0" + feedbackMessage;
        x++;
    }

    return value;
}

$(document).ready(function () {
    $('#continue').click(function() {
        x = 0;
        //loop through the 7 questions and validate. 
        for(let i = 1; i <= 7; i++) {
            if(document.getElementById("q" + i + "Select").nodeName === "TEXTAREA") {
                localStorage.setItem("preq" + i, validate_form("q" + i + "Select", "q" + i + "Feedback", "Please write your response"));
            } else {
                localStorage.setItem("preq" + i, validate_form("q" + i + "Select", "q" + i + "Feedback", "Please select an option"));
            }
        }
            
        // if all of the input is valid (x is incremented when an invalid input is found)
        // If any are invalid, don't continue to next page. 
        if (x == 0) {
            $("#continue").attr("disabled", "disabled").off('click');
            $("#continue").css("background-color", "#8f8f8f");

            for(let i = 1; i <= 7; i++) {
                writeUserData(db, userId, 'preq' + i, localStorage.getItem("preq" + i))
            }

            document.getElementById("endloading").style.display = "block"

            setTimeout(function () {
                document.getElementById("endloading").style.display = "none"
                localStorage.getItem("taskOrder") == 0 ? location.href = './tutorialVideo-systemU' : location.href = './tutorialVideo-systemV'
            }, 5000)
        }
    });
    
    // if input has been changed and is valid, remove the info circle and feedback message
    function changed(formId, feedbackId) {
        $(formId).change(function () {
            document.getElementById(feedbackId).innerHTML = "";
        });
    }
    
    for(let i = 1; i <= 7; i++) {
        changed("#q" + i + "Select", "q" + i + "Feedback")
    }
});