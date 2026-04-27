import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-app.js";
import { getDatabase, ref, set } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-database.js";

let url_prefix = "http://127.0.0.1:5000/";

var userId = localStorage.getItem("userId")

var x = 0

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
    set(ref(db, 'users/' + userId +  '/postStudy/' + question), {
      answer : answer
    });
  }

function validate_form(formId, feedbackId, feedbackMessage) {
    var value = "";
    if (document.getElementById(formId).checkValidity()) {
        document.getElementById(feedbackId).innerHTML = "";
        value = $("#" + formId).val();
        // console.log(value);
    } else {
        if(formId != "q10Select") {
            document.getElementById(feedbackId).innerHTML = '<i class="fa fa-info-circle" style="color:red"></i>' +
            "\xa0" +
            feedbackMessage;
        // console.log(formId)
            x = x + 1;
        }
    }
    return value;
}

$(document).ready(function () {
    $('#q1Select').change(function () {
        document.getElementById("q1Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q2Select').change(function () {
        document.getElementById("q2Feedback").innerHTML = "";
        var temp = $("#q2Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q2Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q2Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q2ExtensionText').change(function () {
        document.getElementById("q2ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q3Select').change(function () {
        document.getElementById("q3Feedback").innerHTML = "";
        var temp = $("#q3Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q3Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q3Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q3ExtensionText').change(function () {
        document.getElementById("q3ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q4Select').change(function () {
        document.getElementById("q4Feedback").innerHTML = "";
        var temp = $("#q4Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q4Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q4Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q4ExtensionText').change(function () {
        document.getElementById("q4ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q5Select').change(function () {
        document.getElementById("q5Feedback").innerHTML = "";
        var temp = $("#q5Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q5Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q5Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q5ExtensionText').change(function () {
        document.getElementById("q5ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q6Select').change(function () {
        document.getElementById("q6Feedback").innerHTML = "";
        var temp = $("#q6Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q6Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q6Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q6ExtensionText').change(function () {
        document.getElementById("q6ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q7Select').change(function () {
        document.getElementById("q7Feedback").innerHTML = "";
        var temp = $("#q7Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q7Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q7Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q7ExtensionText').change(function () {
        document.getElementById("q7ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q8Select').change(function () {
        document.getElementById("q8Feedback").innerHTML = "";
        var temp = $("#q8Select").val();
        if (temp == "SuDoCu" || temp == "SBERT") {
            document.getElementById("q8Extension").setAttribute("style", "display:block");
        } else {
            document.getElementById("q8Extension").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q8ExtensionText').change(function () {
        document.getElementById("q8ExtensionFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q9Select').change(function () {
        document.getElementById("q9Feedback").innerHTML = "";
        var temp = $("#q9Select").val();
        if (temp == "Yes") {
            document.getElementById("q9YesResponse").setAttribute("style", "display:block");
        } else {
            document.getElementById("q9YesResponse").setAttribute("style", "display:none");
        }
    });
});

$(document).ready(function () {
    $('#q9YesText').change(function () {
        document.getElementById("q9YesFeedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#q10Select').change(function () {
        // document.getElementById("q10Feedback").innerHTML = "";
    });
});

$(document).ready(function () {
    $('#continue').click(function() {
        console.log("test")
        x = 0
        localStorage.setItem("posq1", validate_form("q1Select", "q1Feedback",
                "Please select an option"));

        let posq2Val = validate_form("q2Select", "q2Feedback", "Please select an option")
        localStorage.setItem("posq2", posq2Val);
        if (posq2Val == "SuDoCu" || posq2Val == "SBERT") {
            localStorage.setItem("posq2Extension", validate_form("q2ExtensionText",
                "q2ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq3Val = validate_form("q3Select", "q3Feedback", "Please select an option")
        localStorage.setItem("posq3", posq3Val);
        if (posq3Val == "SuDoCu" || posq3Val == "SBERT") {
            localStorage.setItem("posq3Extension", validate_form("q3ExtensionText",
                "q3ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq4Val = validate_form("q4Select", "q4Feedback", "Please select an option")
        localStorage.setItem("posq4", posq4Val);
        if (posq4Val == "SuDoCu" || posq4Val == "SBERT") {
            localStorage.setItem("posq4Extension", validate_form("q4ExtensionText",
                "q4ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq5Val = validate_form("q5Select", "q5Feedback", "Please select an option")
        localStorage.setItem("posq5", posq5Val);
        if (posq5Val == "SuDoCu" || posq5Val == "SBERT") {
            localStorage.setItem("posq5Extension", validate_form("q5ExtensionText",
                "q5ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq6Val = validate_form("q6Select", "q6Feedback", "Please select an option")
        localStorage.setItem("posq6", posq2Val);
        if (posq6Val == "SuDoCu" || posq6Val == "SBERT") {
            localStorage.setItem("posq6Extension", validate_form("q6ExtensionText",
                "q6ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq7Val = validate_form("q7Select", "q7Feedback", "Please select an option")
        localStorage.setItem("posq7", posq7Val);
        if (posq7Val == "SuDoCu" || posq7Val == "SBERT") {
            localStorage.setItem("posq7Extension", validate_form("q7ExtensionText",
                "q7ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq8Val = validate_form("q8Select", "q8Feedback", "Please select an option")
        localStorage.setItem("posq8", posq8Val);
        if (posq8Val == "SuDoCu" || posq8Val == "SBERT") {
            localStorage.setItem("posq9Extension", validate_form("q8ExtensionText",
                "q8ExtensionFeedback",
                "Please write a response"
            ));
        }

        let posq9Val = validate_form("q9Select", "q9Feedback", "Please select an option")
        localStorage.setItem("posq9", posq9Val);
        if (posq9Val == "Yes") {
            localStorage.setItem("posq9YesText", validate_form("q9YesText",
                "q9YesFeedback",
                "Please write a response"
            ));
        }

        localStorage.setItem("posq10", `${$("#q10Select").val()}`);

        writeUserData(db, userId, "posq1", localStorage.getItem("posq1"))
        writeUserData(db, userId, "posq2", localStorage.getItem("posq2"))
        writeUserData(db, userId, "posq2Extension", localStorage.getItem("posq2Extension"))
        writeUserData(db, userId, "posq3", localStorage.getItem("posq3"))
        writeUserData(db, userId, "posq3Extension", localStorage.getItem("posq3Extension"))
        writeUserData(db, userId, "posq4", localStorage.getItem("posq4"))
        writeUserData(db, userId, "posq4Extension", localStorage.getItem("posq4Extension"))
        writeUserData(db, userId, "posq5", localStorage.getItem("posq5"))
        writeUserData(db, userId, "posq5Extension", localStorage.getItem("posq5Extension"))
        writeUserData(db, userId, "posq6", localStorage.getItem("posq6"))
        writeUserData(db, userId, "posq6Extension", localStorage.getItem("posq6Extension"))
        writeUserData(db, userId, "posq7", localStorage.getItem("posq7"))
        writeUserData(db, userId, "posq7Extension", localStorage.getItem("posq7Extension"))
        writeUserData(db, userId, "posq8", localStorage.getItem("posq8"))
        writeUserData(db, userId, "posq8Extension", localStorage.getItem("posq8Extension"))
        writeUserData(db, userId, "posq9", localStorage.getItem("posq9"))
        if (posq9Val == "Yes") {
            writeUserData(db, userId, "posq9Yes", localStorage.getItem("posq9YesText"))
        }
        writeUserData(db, userId, "posq10", localStorage.getItem("posq10"))
        
         

        if (x == 0) {
            console.log("locallength", localStorage.length)
            document.getElementById("endloading").style.display = "block"
            setTimeout(function () {
                document.getElementById("endloading").style.display = "none"
                location.href = "./endPage"
            }, 3000)
        }
    });
});