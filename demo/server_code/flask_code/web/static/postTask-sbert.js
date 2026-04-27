import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-app.js";
import { getDatabase, ref, set } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-database.js";

let url_prefix = "http://127.0.0.1:5000/";

var x = 0

var userId = localStorage.getItem("userId")

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

function writeUserData(db, userId, question, answer) {
    set(ref(db, 'users/' + userId + '/postTaskSbert/' + question), {
      answer : answer
    });
}

function validate_form(formId, feedbackId, feedbackMessage) {
    var value = "";
    if (document.getElementById(formId).checkValidity() && formId !== "q13Response") {
        document.getElementById(feedbackId).innerHTML = "";
        value = $("#" + formId).val();
        if (formId == "q2Select" || formId == "q1Select") {
            if (value.length < 3) {
                document.getElementById(feedbackId).innerHTML = '<i class="fa fa-info-circle" style="color:red"></i>' +
            "\xa0" + "Please select at least three states";
                x = x + 1;
            }
        }
        // console.log(value);
    } else {
        if(formId != "q13Response") {
            document.getElementById(feedbackId).innerHTML = '<i class="fa fa-info-circle" style="color:red"></i>' +
            "\xa0" +
            feedbackMessage;
            x = x + 1;
        }
        // console.log(formId)
    }
    return value;
}

let selectTop;


window.onmousedown = function (e) {   
    // this.selected = !this.selected;
    // e.preventDefault();
    var el = e.target;
    if (el.tagName.toLowerCase() == 'option' && el.parentNode.hasAttribute('multiple')) {
        e.preventDefault();

        // toggle selection
        if (el.hasAttribute('selected')) el.removeAttribute('selected');
        else el.setAttribute('selected', '');

        selectTop = el.parentNode.scrollTop;
    }
};

const selects = document.querySelectorAll('select');
for (const select of selects) {
    select.addEventListener('scroll', (e) => {
    if (selectTop) { e.target.scrollTop = selectTop };
    selectTop = 0;
  })
}

// $('select option').on('mousedown', function (e) {
//     this.selected = !this.selected;
//     e.preventDefault();
// });

$(document).ready(function () {
    $('#q1Select').change(function () {
        document.getElementById("q1Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q2Select').change(function () {
        document.getElementById("q2Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q3Select').change(function () {
        document.getElementById("q3Feedback").innerHTML = "";
        var temp = $("#q3Select").val();
        if (temp == "Yes") {
            document.getElementById("q3Yes").setAttribute("style", "display:block");
            document.getElementById("q3No").setAttribute("style", "display:none");
        } 
        else if (temp == "No") {
            document.getElementById("q3No").setAttribute("style", "display:block");
            document.getElementById("q3Yes").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q4Select').change(function () {
        document.getElementById("q4Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q5Select').change(function () {
        document.getElementById("q5Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q6Select').change(function () {
        document.getElementById("q6Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q7Select').change(function () {
        document.getElementById("q7Feedback").innerHTML = "";
        var temp = $("#q7Select").val();
        if (temp == "Yes") {
            document.getElementById("q7Yes").setAttribute("style", "display:block");
            document.getElementById("q7No").setAttribute("style", "display:none");
        } 
        else if (temp == "No") {
            document.getElementById("q7No").setAttribute("style", "display:block");
            document.getElementById("q7Yes").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q8Select').change(function () {
        document.getElementById("q8Feedback").innerHTML = "";
        var temp = $("#q8Select").val();
        if (temp == "Yes") {
            document.getElementById("q8Yes").setAttribute("style", "display:block");
        } 
        else {
            document.getElementById("q8Yes").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q9Select').change(function () {
        document.getElementById("q9Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q10Select').change(function () {
        document.getElementById("q10Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q11Select').change(function () {
        document.getElementById("q11Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q12Select').change(function () {
        document.getElementById("q12Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q13Select').change(function () {
        document.getElementById("q13Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#continue').click(function() {
        x = 0

        localStorage.setItem("post1-sbert", validate_form("q1Select", "q1Feedback",
                "Please select an option"));

        localStorage.setItem("post2-sbert", validate_form("q2Select", "q2Feedback",
        "Please select an option"));

        let post3Val = validate_form("q3Select", "q3Feedback", "Please select an option")
        localStorage.setItem("post3-sbert", post3Val)
        if (post3Val == "Yes") {
            localStorage.setItem("post3Yes-sbert", validate_form("q3YesText",
                "q3YesFeedback",
                "Please write a response"
            ));
        }
        else if (post3Val == "No") {
            localStorage.setItem("post3No-sbert", validate_form("q3NoText",
                "q3NoFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("post4-sbert", validate_form("q4Select", "q4Feedback",
        "Please select an option"));

        localStorage.setItem("post5-sbert", validate_form("q5Select", "q5Feedback",
        "Please select an option"));

        localStorage.setItem("post6-sbert", validate_form("q6Select", "q6Feedback",
        "Please select an option"));

        let post7Val = validate_form("q7Select", "q7Feedback", "Please select an option")
        localStorage.setItem("post7-sbert", post7Val)
        if (post7Val == "Yes") {
            localStorage.setItem("post7Yes-sbert", validate_form("q7YesText",
                "q7YesFeedback",
                "Please write a response"
            ));
        }
        else if (post7Val == "No") {
            localStorage.setItem("post7No-sbert", validate_form("q7NoText",
                "q7NoFeedback",
                "Please write a response"
            ));
        }

        let post8Val = validate_form("q8Select", "q8Feedback", "Please select an option")
        localStorage.setItem("post8-sbert", post8Val)
        if (post8Val == "Yes") {
            localStorage.setItem("post8Yes-sbert", validate_form("q8YesText",
                "q8YesFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("post9-sbert", validate_form("q9Response", "q9Feedback",
        "Please write a response"));

        localStorage.setItem("post10-sbert", validate_form("q10Response", "q10Feedback",
        "Please write a response"));

        localStorage.setItem("post11-sbert", validate_form("q11Response", "q11Feedback",
        "Please write a response"));

        localStorage.setItem("post12-sbert", validate_form("q12Select", "q12Feedback",
        "Please select an option"));

        // localStorage.setItem("post13-sbert", validate_form("q13Response", "q13Feedback",
        // ""));
        localStorage.setItem("post13-sbert", `${$("#q13Response").val()}`);

        if (x == 0) {
            writeUserData(db, userId, "post1-sbert", localStorage.getItem("post1-sbert"))
            writeUserData(db, userId, "post2-sbert", localStorage.getItem("post2-sbert"))
            writeUserData(db, userId, "post3-sbert", localStorage.getItem("post3-sbert"))
            if (post3Val == "Yes") {
                writeUserData(db, userId, "post3Yes-sbert", localStorage.getItem("post3Yes-sbert"))
            }
            else {
                writeUserData(db, userId, "post3No-sbert", localStorage.getItem("post3No-sbert"))
            }
            writeUserData(db, userId, "post4-sbert", localStorage.getItem("post4-sbert"))
            writeUserData(db, userId, "post5-sbert", localStorage.getItem("post5-sbert"))
            writeUserData(db, userId, "post6-sbert", localStorage.getItem("post6-sbert"))
            // if (post6Val == "Yes") {
            //     writeUserData(db, userId, "post6Yes1-sbert", localStorage.getItem("post6Yes1-sbert"))
            //     writeUserData(db, userId, "post6Yes2-sbert", localStorage.getItem("post6Yes2-sbert"))
            //     if (validate_form("q6Yes2Select", "q6Yes2Feedback", "Please select an option") == "Yes") {
            //         writeUserData(db, userId, "post6Yes2Yes-sbert", localStorage.getItem("post6Yes2Yes-sbert"))
            //     }
            // }
            // else {
            //     writeUserData(db, userId, "post6No-sbert", localStorage.getItem("post6No-sbert"))
            // }
            writeUserData(db, userId, "post7-sbert", localStorage.getItem("post7-sbert"))
            if (post7Val == "Yes") {
                writeUserData(db, userId, "post7Yes-sbert", localStorage.getItem("post7Yes-sbert"))
            }
            else {
                writeUserData(db, userId, "post7No-sbert", localStorage.getItem("post7No-sbert"))
            }
            writeUserData(db, userId, "post8-sbert", localStorage.getItem("post8-sbert"))
            if (post8Val == "Yes") {
                writeUserData(db, userId, "post8Yes-sbert", localStorage.getItem("post8Yes-sbert"))
            }
            writeUserData(db, userId, "post9-sbert", localStorage.getItem("post9-sbert"))
            writeUserData(db, userId, "post10-sbert", localStorage.getItem("post10-sbert"))
            writeUserData(db, userId, "post11-sbert", localStorage.getItem("post11-sbert"))
            writeUserData(db, userId, "post12-sbert", localStorage.getItem("post12-sbert"))
            writeUserData(db, userId, "post13-sbert", localStorage.getItem("post13-sbert"))

            document.getElementById("endloading").style.display = "block"
            setTimeout(function () {
                document.getElementById("endloading").style.display = "none"
                if (localStorage.getItem("taskOrder") == 0) {
                    location.href = './postStudy'
                }
                else {
                    location.href = './tutorialVideo-systemU'
                }
            }, 5000)
        }
    });
})