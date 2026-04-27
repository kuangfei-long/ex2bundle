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
    set(ref(db, 'users/' + userId + '/postTaskSudocu/' + question), {
      answer : answer
    });
}

function validate_form(formId, feedbackId, feedbackMessage) {
    var value = "";
    if (document.getElementById(formId).checkValidity() && formId !== "q16Response") {
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
        if (formId != "q16Response") {
            document.getElementById(feedbackId).innerHTML = '<i class="fa fa-info-circle" style="color:red"></i>' +
            "\xa0" +
            feedbackMessage;
            x = x + 1;
        }
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
        var temp = $("#q6Select").val();
        if (temp == "Yes") {
            document.getElementById("q6Yes1").setAttribute("style", "display:block");
            document.getElementById("q6Yes2").setAttribute("style", "display:block");
            document.getElementById("q6No").setAttribute("style", "display:none");
        } 
        else if (temp == "No") {
            document.getElementById("q6No").setAttribute("style", "display:block");
            document.getElementById("q6Yes1").setAttribute("style", "display:none");
            document.getElementById("q6Yes2").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q6Yes2Select').change(function () {
        document.getElementById("q6Yes2YesFeedback").innerHTML = "";
        var temp = $("#q6Yes2Select").val();
        if (temp == "Yes") {
            document.getElementById("q6Yes2Yes").setAttribute("style", "display:block");
        } 
        else {
            document.getElementById("q6Yes2Yes").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q7Select').change(function () {
        document.getElementById("q7Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q8Select').change(function () {
        document.getElementById("q8Feedback").innerHTML = "";
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
        var temp = $("#q10Select").val();
        if (temp == "Yes") {
            document.getElementById("q10Yes").setAttribute("style", "display:block");
            document.getElementById("q10No").setAttribute("style", "display:none");
        } 
        else if (temp == "No") {
            document.getElementById("q10No").setAttribute("style", "display:block");
            document.getElementById("q10Yes").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q11Select').change(function () {
        document.getElementById("q11Feedback").innerHTML = "";
        var temp = $("#q11Select").val();
        if (temp == "Yes") {
            document.getElementById("q11Yes").setAttribute("style", "display:block");
        } 
        else {
            document.getElementById("q11Yes").setAttribute("style", "display:none");
        }
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
    $('#q14Select').change(function () {
        document.getElementById("q14Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q15Select').change(function () {
        document.getElementById("q15Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q16Select').change(function () {
        document.getElementById("q16Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#continue').click(function() {
        x = 0

        localStorage.setItem("post1-sudocu", validate_form("q1Select", "q1Feedback",
                "Please select an option"));

        localStorage.setItem("post2-sudocu", validate_form("q2Select", "q2Feedback",
        "Please select an option"));

        let post3Val = validate_form("q3Select", "q3Feedback", "Please select an option")
        localStorage.setItem("post3-sudocu", post3Val)
        if (post3Val == "Yes") {
            localStorage.setItem("post3Yes-sudocu", validate_form("q3YesText",
                "q3YesFeedback",
                "Please write a response"
            ));
        }
        else if (post3Val == "No") {
            localStorage.setItem("post3No-sudocu", validate_form("q3NoText",
                "q3NoFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("post4-sudocu", validate_form("q4Select", "q4Feedback",
        "Please select an option"));

        localStorage.setItem("post5-sudocu", validate_form("q5Select", "q5Feedback",
        "Please select an option"));

        let post6Val = validate_form("q6Select", "q6Feedback", "Please select an option")
        localStorage.setItem("post6-sudocu", post6Val)
        if (post6Val == "Yes") {
            localStorage.setItem("post6Yes1-sudocu", validate_form("q6Yes1Response",
                "q6Yes1Feedback",
                "Please write a response"
            ));
            let post6Yes2Val = validate_form("q6Yes2Select", "q6Yes2Feedback", "Please select an option")
            localStorage.setItem("post6Yes2-sudocu", post6Yes2Val)
            if (post6Yes2Val == "Yes") {
                localStorage.setItem("post6Yes2Yes-sudocu", validate_form("q6Yes2YesResponse",
                "q6Yes2YesFeedback",
                "Please write a response"
                ));
            }
        }
        else if (post6Val == "No") {
            localStorage.setItem("post6No-sudocu", validate_form("q6NoResponse",
                "q6NoFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("post7-sudocu", validate_form("q7Select", "q7Feedback",
        "Please select an option"));

        localStorage.setItem("post8-sudocu", validate_form("q8Select", "q8Feedback",
        "Please select an option"));

        localStorage.setItem("post9-sudocu", validate_form("q9Select", "q9Feedback",
        "Please select an option"));

        let post10Val = validate_form("q10Select", "q10Feedback", "Please select an option")
        localStorage.setItem("post10-sudocu", post10Val)
        if (post10Val == "Yes") {
            localStorage.setItem("post10Yes-sudocu", validate_form("q10YesText",
                "q10YesFeedback",
                "Please write a response"
            ));
        }
        else if (post10Val == "No") {
            localStorage.setItem("post10No-sudocu", validate_form("q10NoText",
                "q10NoFeedback",
                "Please write a response"
            ));
        }

        let post11Val = validate_form("q11Select", "q11Feedback", "Please select an option")
        localStorage.setItem("post11-sudocu", post11Val)
        if (post11Val == "Yes") {
            localStorage.setItem("post11Yes-sudocu", validate_form("q11YesText",
                "q11YesFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("post12-sudocu", validate_form("q12Response", "q12Feedback",
        "Please write a response"));

        localStorage.setItem("post13-sudocu", validate_form("q13Response", "q13Feedback",
        "Please write a response"));

        localStorage.setItem("post14-sudocu", validate_form("q14Response", "q14Feedback",
        "Please write a response"));

        localStorage.setItem("post15-sudocu", validate_form("q15Select", "q15Feedback",
        "Please select an option"));

        // localStorage.setItem("post16-sudocu", validate_form("q16Response", "q16Feedback",
        // ""));
        localStorage.setItem("post16-sudocu", `${$("#q16Response").val()}`);

        if (x == 0) {
            writeUserData(db, userId, "post1-sudocu", localStorage.getItem("post1-sudocu"))
            writeUserData(db, userId, "post2-sudocu", localStorage.getItem("post2-sudocu"))
            writeUserData(db, userId, "post3-sudocu", localStorage.getItem("post3-sudocu"))
            if (post3Val == "Yes") {
                writeUserData(db, userId, "post3Yes-sudocu", localStorage.getItem("post3Yes-sudocu"))
            }
            else {
                writeUserData(db, userId, "post3No-sudocu", localStorage.getItem("post3No-sudocu"))
            }
            writeUserData(db, userId, "post4-sudocu", localStorage.getItem("post4-sudocu"))
            writeUserData(db, userId, "post5-sudocu", localStorage.getItem("post5-sudocu"))
            writeUserData(db, userId, "post6-sudocu", localStorage.getItem("post6-sudocu"))
            if (post6Val == "Yes") {
                writeUserData(db, userId, "post6Yes1-sudocu", localStorage.getItem("post6Yes1-sudocu"))
                writeUserData(db, userId, "post6Yes2-sudocu", localStorage.getItem("post6Yes2-sudocu"))
                if (validate_form("q6Yes2Select", "q6Yes2Feedback", "Please select an option") == "Yes") {
                    writeUserData(db, userId, "post6Yes2Yes-sudocu", localStorage.getItem("post6Yes2Yes-sudocu"))
                }
            }
            else {
                writeUserData(db, userId, "post6No-sudocu", localStorage.getItem("post6No-sudocu"))
            }
            writeUserData(db, userId, "post7-sudocu", localStorage.getItem("post7-sudocu"))
            writeUserData(db, userId, "post8-sudocu", localStorage.getItem("post8-sudocu"))
            writeUserData(db, userId, "post9-sudocu", localStorage.getItem("post9-sudocu"))
            writeUserData(db, userId, "post10-sudocu", localStorage.getItem("post10-sudocu"))
            if (post10Val == "Yes") {
                writeUserData(db, userId, "post10Yes-sudocu", localStorage.getItem("post10Yes-sudocu"))
            }
            else {
                writeUserData(db, userId, "post10No-sudocu", localStorage.getItem("post10No-sudocu"))
            }
            writeUserData(db, userId, "post11-sudocu", localStorage.getItem("post11-sudocu"))
            if (post11Val == "Yes") {
                writeUserData(db, userId, "post11Yes-sudocu", localStorage.getItem("post11Yes-sudocu"))
            }
            writeUserData(db, userId, "post12-sudocu", localStorage.getItem("post12-sudocu"))
            writeUserData(db, userId, "post13-sudocu", localStorage.getItem("post13-sudocu"))
            writeUserData(db, userId, "post14-sudocu", localStorage.getItem("post14-sudocu"))
            writeUserData(db, userId, "post15-sudocu", localStorage.getItem("post15-sudocu"))
            writeUserData(db, userId, "post16-sudocu", localStorage.getItem("post16-sudocu"))


            document.getElementById("endloading").style.display = "block"
            setTimeout(function () {
                document.getElementById("endloading").style.display = "none"
                if (localStorage.getItem("taskOrder") == 0) {
                    location.href = './tutorialVideo-systemV'
                }
                else {
                    location.href = './postStudy'
                }
            }, 5000)
        }
    });
})