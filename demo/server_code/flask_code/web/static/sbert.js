import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-app.js";
import { getDatabase, ref, set } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-database.js";


let url_prefix = "http://127.0.0.1:5000/";
$(document).ready(function () {
  let nTopics = 10;
  let bounds = [];                   // list to hold the generated ILP topic score constraint bounds used by SuDocu
  let data_states = [];              // list of the various state names
  let data_sentences = [];           // list of sentences for currently displayed state doc
  let sentenceArray = [];            // list of sentence used to display current state doc
  let submittedSummary = [];         // list of example summaries submitted by the user
  let keywordInfo = [];              // list containing a history of keyword searches
  let currentLabel = "";             // the label (name) of the doc currently selected doc in the Input section
  let prevLabel = "";                // label of the previously selected doc
  var userID = localStorage.getItem("userId");
  
  let submitButton = document.getElementById("submitSummary");
  let learnSummaryButton = document.getElementById("button_learnSummary");
  let dropdown_input = document.getElementById("inputDocumentSelector");
  let dropdown_output = document.getElementById("outputDocumentSelector");

  // list to hold JSONS for all user interactions
  let data_interactions = []
  
  var recordInteractions = true;
  let showExplanation = false; //Show explanation window after user has entered the summary
  let modifiedTopicConstraints = [];
  let currOpenTopic = -1;
  let displayBarChart = 1;

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
      set(ref(db, 'users/' + userId + '/SbertTask/' + question), {
        answer : answer
      });
  }
  
  //Check if user has visited the page
  if (window.localStorage.getItem("intilized") === null) {
    initialize_localStorage();
  } else {
    load_LocalStorage();
  }
  
  submitButton.setAttribute("disabled", "disabled");
  learnSummaryButton.setAttribute("disabled", "disabled");
  dropdown_output.setAttribute("disabled", "disabled");
  $("#button_learnSummary").tooltip();

  $("#button_completeTask").click(function() {
    $(".modal-title").text("Finish Confirmation");
    $(".modal-body").text("Are you sure you want to complete the task?");
    $('#exampleModal').modal("toggle");
    $("#exampleModal").on("click",".btn.btn-secondary", function(){
      dumpAllUserInteraction(); //Data goes to local storage and dump data to the server
      location.href = './postTask-systemV'
    });
    $(".btn.btn-primary").hide();
  })

    //disable topic importance section, reset sliders to 0
    function disableOldSummary() {
      $(".subHeader").css("background-color", "#8f8f8f");
      $("#outputDocumentSelector").prop("disabled", true);
      $("#generated").children().remove();
      $("#outputDocumentSelector").prop("selectedIndex", 0);
      $(".warnMes2").prop("style", "display: flex");
      if(Object.keys(submittedSummary).length < 2) {
        $(".warnMes2 #warnMesText").text("Please submit at least 2 example summaries and analyze your changes.")
      } else {
        $(".warnMes2 #warnMesText").text("Please analyze your changes.")
      }
    }

  // this ajac request initially populates the input document selection dropdown. 
  $.ajax({
    url: url_prefix + "get_states_sbert",
    async: true,
    type: "GET",
    dataType: "json",
    success: function (data) {
      data_states = data;

      window.localStorage.setItem("data_states", JSON.stringify(data_states));
      
      for (let i = 0; i < data_states.length; i++) {
        //dynamically create option
        let option_input = document.createElement("OPTION");
        option_input.innerHTML = data_states[i].state_name.replaceAll('_', ' ');
        option_input.value = "doc" + data_states[i].state_id.toString(10);
        dropdown_input.options.add(option_input);

        let option_output = document.createElement("OPTION");
        option_output.innerHTML = data_states[i].state_name;
        option_output.value =
          "learnedSummary" + data_states[i].state_id.toString(10);
        dropdown_output.options.add(option_output);

        let option_topic = document.createElement("OPTION");
        option_topic.innerHTML = data_states[i].state_name;
        option_topic.value = "topics" + (data_states[i].state_id).toString(10);
        // dropdown_topic.options.add(option_topic);
      }
    },
  });

  // populate the accordion headers with the appropriate topics on start up
  populateTopicKeywords(-1); //-1 all statistics, index 0 from the first state

  // user-feedback popovers for various buttons
  $("#genSumInfoIcon").popover("enable");
  $("#sumSelectorInfoIcon").popover("enable");
  $("#exSumInfoIcon").popover("enable");
  $("#PaQLInfoIcon").popover("enable");
  $('.d-inline-block').tooltip();
  $('.d-inline-block').tooltip("enable");
  $("#submitSummary").popover({ trigger: "manual", placement: "top" });
  // $("#button_learnSummary").popover({ trigger: "manual", placement: "top" });

  $('[data-toggle="popover"]').popover({
    container: 'body'
  });

  $(".document").hide();
  // function used to display selected documents
  $("#inputDocumentSelector").change(function () {
    currentLabel = $(this).val();
    let idx = parseInt(currentLabel.substring(3));

    let docId = idx.toString(10);
    
    let docName = ""

    for (let j = 0; j < data_states.length; j++) {
      if (data_states[j].state_id == idx) {
        docName = data_states[j].state_name
      }
    }
    
    
    if (document.getElementById("doc" + docId) === null) {
      let sampleContent = document.createElement("div");
      sampleContent.setAttribute("id", "doc" + docId);
      sampleContent.setAttribute("class", "document");
      document.getElementById("docContentSbert").appendChild(sampleContent);
    }

    if (!sentenceArray.some((o) => o.document_id === currentLabel)) {
      sentenceArray.push({
        document_id: currentLabel,
        selected: [],
        submitted: [],
      });
    }

    for (let i = 0; i < sentenceArray.length; i++) {
      for (let j = 0; j < sentenceArray[i].selected.length; j++) {
        if (document.getElementById(sentenceArray[i].selected[j]) === null) {
          continue;
        }
        document
          .getElementById(sentenceArray[i].selected[j])
          .setAttribute("class", "normal_sentenceSbert");
      }
      sentenceArray[i].selected = [];
    }

    window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));

    //Pull sentences and populates initialized structures
    $.ajax({
      url: url_prefix + "get_sentences?state_id=" + idx,
      async: true,
      type: "GET",
      dataType: "json",
      beforeSend: function () {
        $("#loaderSbert").show();
        $("#loader_background").show();
        $(".document").hide();
      },
      success: function (data) {
        $("#" + currentLabel).show();
        data_sentences = data;
        let currStateId = idx;

        window.localStorage.setItem("data_sentences", JSON.stringify(data_sentences));

        for (let j = 0; j < data_sentences.length; j++) {
          let span = document.createElement("SPAN");
          let sentId = (
            (currStateId + 1) * 1000000 +
            data_sentences[j].sentence_id
          ).toString(10);
          span.setAttribute("id", "sent" + sentId);
          span.setAttribute("class", "normal_sentenceSbert");
          span.setAttribute("title", "Click to select the sentence");
          span.onclick = highlightSentence;
          span.textContent = data_sentences[j].text;
          if (document.getElementById("doc" + currStateId.toString(10)) != null) {
            document.getElementById("doc" + currStateId.toString(10)).appendChild(span);
          }
          
          let space_span = document.createElement("SPAN");
          space_span.textContent = " ";
          if (document.getElementById("doc" + currStateId.toString(10)) != null) {
            document.getElementById("doc" + currStateId.toString(10)).appendChild(space_span);
          }
          
        }

        // If state had previously selected sentences, set their class to show selected sentences
        let currObj = submittedSummary.find((o) => o.state_id === idx);
        if (currObj !== undefined) {
          for (let k = 0; k < currObj.sentence_ids.length; k++) {
            let sentUnit_s = currObj.sentence_ids[k];
            document
              .getElementById(sentUnit_s)
              .setAttribute("class", "selectedSbert");
          }
        }

        document.getElementById("searchInput").value = "";
      },
      complete: function () {
        $("#loaderSbert").hide();
        $("#loader_background").hide();
      },
    });

    //if new state is selected that isnt already in the list
    if (document.getElementById(docName) === null) {
      submitButton.removeAttribute("disabled");
      $("#submitSummary").text("Submit Summary");
      $("#subupButton").tooltip('dispose').attr('data-bs-original-title', "Submit your summary").tooltip();
    } else {
      $("#submitSummary").text("Update Summary");
      $("#subupButton").tooltip('dispose').attr('data-bs-original-title', "Update your summary").tooltip();
    }

    if (document.getElementById(prevLabel) !== null) {
      document.getElementById(prevLabel).remove();
    }
    prevLabel = currentLabel;

    window.localStorage.setItem("currentLabel", currentLabel);
    window.localStorage.setItem("prevLabel", prevLabel);
  });

  //Drop down button in 
  $("#topicDocumentSelector").change(function () {
    console.log("te")
    $(".generatedDoc").hide();

    let topic_currentLabel = $(this).val();
    let idx = parseInt(topic_currentLabel.substring(6));
    // let docId = data_states[idx].state_id.toString(10);
    populateTopicKeywords(idx);
    logInteraction("display_topic_keywords", `displaying wordcloud for document id: ${idx}, and label: ${topic_currentLabel}`);

  });

  let selectedState = "None";
  $(".generatedDoc").hide();

  // function to actually generate a summary. 
  // checks if bounds have been modified. If so, use modified bounds, otherwise use the default learned bounds
  $('#outputDocumentSelector').change(function () {
    getSummAjax();
    $("#button_completeTask").prop('disabled', false);
  });

  function getSummAjax() {
    $(".generatedDoc").hide();
    // get the value of the currently selected item
    let select = document.getElementById('outputDocumentSelector');
    let currentLearnedLabel = select.options[select.selectedIndex].value;
    let stateName = select.options[select.selectedIndex].textContent;
    // get the name of the selected state from the dropdown
    selectedState = $("#outputDocumentSelector option:selected").text();
    $("#" + currentLearnedLabel).show();

    let generated_summary_log = {}
    let idx = parseInt(currentLearnedLabel.substring(14));
    // let docId = data_states[idx].state_id.toString(10);
    let docId = idx.toString(10);
    
    let learnedContent = document.createElement("div");
    learnedContent.setAttribute("id", "learnedSummary" + docId);
    learnedContent.setAttribute("class", "generatedDoc");
    document.getElementById("generated").innerHTML = "";
    document.getElementById("generated").appendChild(learnedContent);

    let submittedSummary_server = makeExampleSummaries();

    let t1 = window.setTimeout(() => {
      $("#wait").text("Taking longer than expected.");
    }, 4000);
    let t2 = window.setTimeout(() => {
      $("#wait").text("Just a little longer.");
    }, 8000);
    $.ajax({
      url: url_prefix + "get_summary",
      async: true,
      type: "POST",
      data: {
        user_id: userID,
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
      },
      //show loading
      beforeSend: function () {
        $("#loaderSbert").show();
        $("#loader_background").show();
        $("#wait").show();
        t1;
        t2;
      },
      //remove loading
      success: function (data) {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
        $("#loaderSbert").hide();
        $("#loader_background").hide();
        $("#wait").text("Please Wait.");
        $("#wait").hide();

        let summary = data.summary;
        let default_summ = data.default;
        let summ_indicies = data.summary_indicies

        generated_summary_log['state_id'] = docId
        generated_summary_log['state_name'] = stateName
        generated_summary_log['examples'] = submittedSummary_server
        generated_summary_log['summary_indicies'] = summ_indicies
        generated_summary_log['default_summ'] = default_summ
        
        logInteraction("json_generate_summary", JSON.stringify(generated_summary_log));


        document.getElementById("learnedSummary" + docId.toString(10)).innerHTML =
          summary;

        if (default_summ == true) {
          $(".modal-title").text("Topic Score Constraints too strict!");
          $(".modal-body").text("No solution could be found and a default summary was returned.");
          $('#exampleModal').modal("toggle");
          $("#exampleModal").on("click",".btn.btn-secondary", function(){
            $('#exampleModal').modal("toggle");
          });
          $(".btn.btn-primary").hide();
        }
      },
    });
  }

  let currentId = "";

  function sentenceIsSelected(targetSentId) {
    for (let i = 0; i < sentenceArray.length; i++) {
      if (sentenceArray[i].selected.includes(targetSentId)) {
        return true;
      }
    }
    return false;
  }

  function sentenceIsSubmitted(targetSent) {
    for (let i = 0; i < sentenceArray.length; i++) {
      if (sentenceArray[i].submitted.includes(targetSent)) {
        return true;
      }
    }
    return false;
  }

  //Highlight the sentence when the sentence is clicked
  function highlightSentence() {
    currentId = this.id;
    let curr = document.getElementById(currentId);
    let selectedText = document.getElementById(currentId).textContent;
    let currObj = sentenceArray.find((o) => o.document_id === currentLabel);
    if (sentenceIsSubmitted(currentId)) {
      curr.setAttribute("class", "normal_sentenceSbert");
      const index = currObj.submitted.findIndex((item) => item === currentId);
      if (index > -1) {
        currObj.submitted.splice(index, 1);
      }
    } else if (!sentenceIsSelected(currentId)) {
      curr.setAttribute("class", "selectedSbert");
      currObj.selected.push(currentId);
    } else if (sentenceIsSelected(currentId)) {
      curr.setAttribute("class", "normal_sentenceSbert");
      const index = currObj.selected.findIndex((item) => item === currentId);
      if (index > -1) {
        currObj.selected.splice(index, 1);
      }
    }
    $(".selected").attr("title", "click to unselect the sentence");
    $(".normal_sentenceSbert").attr("title", "click to select the sentence");

    window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));
  }

  $("#searchInput").keyup(function () {
    let inputText = document.getElementById("searchInput").value.trim();
    let currDocDiv = document.getElementById(currentLabel);

    let filter = inputText.toUpperCase();
    let spanArray = currDocDiv.getElementsByTagName("span");

    // submit the data to the server to be logged
    logInteraction("searched_keyword", filter);
    
    // highlight searched term in spans
    var instance = new Mark([...spanArray]);
    instance.unmark(); //Remove old stuff
    instance.mark(inputText, {
      "accuracy": "partially",
      ignorePunctuation: ["'"],
      "separateWordSearch": false,
    });
    
    $("mark").css("background-color", "#e89664");
    
    // this work displays the relevent sentences in the doc page
    for (let i = 0; i < spanArray.length; i++) {
      if (filter === "" || spanArray[i].textContent.toUpperCase().split(" ").indexOf(filter) > -1) {
        spanArray[i].style.display = "";
      } else {
        spanArray[i].style.display = "none";
      }
    }
  });
  // helper function to generate a "summary" for the submittedSummary list from the text currently
  //     highlighted in the input your examples test box
  $("#submitSummary").click(function () {
    $('#summaryWarn').hide();
    if($("#submitSummary").text() == "Submit Summary"){
      let currObj = sentenceArray.find((o) => o.document_id === currentLabel);

      if (currObj === undefined || currObj.selected.length === 0) {
        $("#submitSummary").popover("hide");
        $(".modal-title").text("Invalid Submission");
        $(".modal-body").text("Please select at least one sentence.");
        $('#exampleModal').modal("toggle");
        $("#exampleModal").on("click",".btn.btn-secondary", function(){
          $('#exampleModal').modal("toggle");
        });
        $(".btn.btn-primary").hide();
        return;
      } else {
        $("#submitSummary").popover("toggle");
        setTimeout(function () {
          $("#submitSummary").popover("hide");
        }, 2000);
      }
      for (let i = 0; i < currObj.selected.length; i++) {
        console.log(currObj.selected[i])
        currObj.submitted.push(currObj.selected[i]);
        document
          .getElementById(currObj.submitted[i])
          .setAttribute("class", "selectedSbert");
      }
      currObj.selected = [];
      let idx = parseInt(currentLabel.substring(3));
  
      let docName = ""
  
      for (let j = 0; j < data_states.length; j++) {
        if (data_states[j].state_id == idx) {
          docName = data_states[j].state_name
        }
      }
  
      // $("#submitSummary").text("Update Summary");
  
      $("#submitSummary").text("Update Summary");
      $("#subupButton").tooltip('dispose').attr('data-bs-original-title', "Update your summary").tooltip();
      let textBox = document.createElement("div");
      textBox.setAttribute("id", docName);
      let filterBtn = document.createElement("div");
      filterBtn.setAttribute("class", "filter-button");
      filterBtn.setAttribute("id", "filter-" + currentLabel);
      filterBtn.setAttribute("title", "Click to select tab");
      filterBtn.append(docName.replaceAll('_', ' '));
      filterBtn.onclick = filterSubmission;
      $(".summaryStatesSbert").append(filterBtn);

      let minimizeBtn = document.createElement("div");
      minimizeBtn.setAttribute("class", "minimize-button");
      minimizeBtn.setAttribute("id", "minimize-" + currentLabel);
      minimizeBtn.setAttribute("title", "Remove this summary");
      minimizeBtn.onclick = filterSubmission;
      minimizeBtn.innerHTML = "&#8722";
      
      let modalWasClosed = 0;
      let closeBtn = document.createElement("div");
      closeBtn.setAttribute("class", "close-button-sbert");
      closeBtn.setAttribute("id", "close-" + currentLabel);
      closeBtn.setAttribute("title", "Remove this summary");

      closeBtn.onclick = () => {
        modalWasClosed = 0;
        $(".modal-title").text("Are you sure you want remove this example summary?");
        $(".modal-body").text("It will be permanently deleted.");
        $('#exampleModal').modal("toggle");
        $("#exampleModal").on("click",".btn.btn-secondary", function(){
          if(modalWasClosed == 0){
            modalWasClosed = 1;
            removeSubmission(closeBtn.id);
          }
          $('#exampleModal').modal("toggle");
        });
        $(".btn.btn-primary").show();
        $("#exampleModal").on("click",".btn.btn-primary", function(){
          $('#exampleModal').modal("toggle");
          modalWasClosed = 1;
        });
      }
      $('#exampleModal').data('bs.modal', null);
      $('#exampleModal').modal({backdrop:'static', keyboard:false});
      
      closeBtn.innerHTML = "&#x2715";

      let summaryHeader = document.createElement("div");
      summaryHeader.setAttribute("class", "summaryHeader");
      $(summaryHeader).append(
        "<div style='display: block; float: left'>" + docName.replaceAll('_', ' ') + "</div>"
      );
      summaryHeader.appendChild(minimizeBtn);
      $(`#filter-${currentLabel}`).append(closeBtn);
      // summaryHeader.textContent = docName;
  
      let summaryText = document.createElement("div");
      summaryText.setAttribute("class", "summaryText");
      currObj.submitted.sort();
  
      let sentence_ids = [];
      for (let j = 0; j < currObj.submitted.length; j++) {
        sentence_ids.push(currObj.submitted[j]);
      }
  
      // create array for the example summary
      let new_sum = {
        state_id: idx,
        state_name: docName,
        sentence_ids: [],
      };
  
      // add the new summary to the array of summaries
      submittedSummary.push({
        state_id: idx,
        state_name: docName,
        sentence_ids: sentence_ids,
      });
      submittedSummary.sort((a, b) => a.state_id - b.state_id);
  
      // update the ids in the new summary to be the actual data ids
      for (let j = 0; j < sentence_ids.length; j++) {
        let reformattedId = parseInt(sentence_ids[j].substring(6));
        new_sum.sentence_ids[j] = reformattedId;
      }
  
      // submit the data to the server to be logged
      logInteraction("json_example", JSON.stringify(new_sum));
  
      let content = "";
      if (currObj.submitted.length === 0) {
        return;
      }
      for (let i = 0; i < currObj.submitted.length; i++) {
        // un-highlight searched term in spans
        let curElement = document.getElementById(currObj.submitted[i]);
        var instance = new Mark(curElement);
        instance.unmark();
        
        let new_content = curElement.innerHTML;
        
        content = content.concat(
          " " + new_content
        );
      }
      summaryText.textContent = content;
      textBox.appendChild(summaryHeader);
      textBox.appendChild(summaryText);
      $(".exampleSummaries").append(textBox);
      $(`#${docName}`).hide();
      window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));
  
      if (Object.keys(submittedSummary).length >= 2) {
        learnSummaryButton.removeAttribute("disabled");
      }
    } else if ($("#submitSummary").text() == "Update Summary") {
      let currObj = sentenceArray.find((o) => o.document_id === currentLabel);
      let idx = parseInt(currentLabel.substring(3));
      let docName = "";
      
      for (let j = 0; j < data_states.length; j++) {
        if (data_states[j].state_id == idx) {
          docName = data_states[j].state_name
        }
      }

      let currTextBox = document
        .getElementById(docName)
        .getElementsByClassName("summaryText")[0];
      for (let i = 0; i < currObj.selected.length; i++) {
        currObj.submitted.push(currObj.selected[i]);
        document
          .getElementById(currObj.submitted[currObj.submitted.length - 1])
          .setAttribute("class", "selectedSbert");
      }      
      currObj.selected = [];
      // get the current summary for this state
      let currObj_sub = submittedSummary.find((o) => o.state_id === idx);
      let updated_sum = {
        state_id: currObj_sub.state_id,
        state_name: currObj_sub.state_name,
        sentence_ids: []
      };

      currObj_sub.sentence_ids = [];
      
      // add the new 
      for (let j = 0; j < currObj.submitted.length; j++) {
        currObj_sub.sentence_ids.push(currObj.submitted[j]);
        updated_sum.sentence_ids.push(parseInt(currObj.submitted[j].substring(6)));
      }


      // submit the data to the server to be logged
      logInteraction("json_example_update", JSON.stringify(updated_sum));

      let content = "";
      currObj.submitted.sort();
      for (let i = 0; i < currObj.submitted.length; i++) {
        // un-highlight searched term in spans
        let curElement = document.getElementById(currObj.submitted[i]);
        var instance = new Mark(curElement);
        instance.unmark({
          "accuracy": {
            "value": "exactly",
            "limiters": [",",".","'",";",":","[","]","(",")"]
          },
          ignorePunctuation: ["'"],
          "separateWordSearch": false,
        });

        content = content.concat(
          " " + document.getElementById(currObj.submitted[i]).innerHTML
        );
      }

      if(content == "") {
        $(".modal-title").text("Invalid Submission");
        $(".modal-body").text("Cannot submit an empty summary.");
        $('#exampleModal').modal("toggle");
        $("#exampleModal").on("click",".btn.btn-secondary", function(){
          $('#exampleModal').modal("toggle");
        });
        $(".btn.btn-primary").hide();
        return;
      }
      currTextBox.textContent = content;

      window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));
    }
    
    window.localStorage.setItem("submittedSummary", JSON.stringify(submittedSummary));
    if($(".subHeader").css("background-color") !== "rgb(143, 143, 143)") {
      disableOldSummary();
    }
  });

  function filterSubmission() {
    let idx = parseInt(this.id.match(/\d+/g));
    let targetDoc = this.id.split('-')[1];
    let docName = "";

    for (let j = 0; j < data_states.length; j++) {
      if (data_states[j].state_id == idx) {
        docName = data_states[j].state_name
      }
    }
    if($(`#filter-${targetDoc}`).attr('title') == "Click to unselect tab") {
      $(`#filter-${targetDoc}`).prop('title', 'Click to select tab');
      $(`#${docName}`).hide();
      $(`#filter-${targetDoc}`).css("background", "white");
      $(`#filter-${targetDoc}`).css("color", "black");
      $(`#filter-${targetDoc}`).hover(function() {
        $(`#filter-${targetDoc}`).css("background", "#D66420");
        $(`#filter-${targetDoc}`).css("color", "white");
        },
        function() {
          $(`#filter-${targetDoc}`).css("background", "white");
          $(`#filter-${targetDoc}`).css("color", "black");
        })
    } else {
      $(`#filter-${targetDoc}`).prop('title', 'Click to unselect tab');
      $(`#${docName}`).show();
      $(`#filter-${targetDoc}`).css("background", "#D66420");
      $(`#filter-${targetDoc}`).css("color", "white");
      $(`#filter-${targetDoc}`).hover(function() {
        $(`#filter-${targetDoc}`).css("background", "white");
        $(`#filter-${targetDoc}`).css("color", "black");},
        function() {
          $(`#filter-${targetDoc}`).css("background", "#D66420");
          $(`#filter-${targetDoc}`).css("color", "white");
        })
    }
  }
  // help function to remove a summary from the list of submitted summaries
  function removeSubmission(id) {
    let idx = parseInt(id.substring(9));
    let targetDoc = id.substring(6);
    let docName = "";

    for (let j = 0; j < data_states.length; j++) {
      if (data_states[j].state_id == idx) {
        docName = data_states[j].state_name
      }
    }
    document.getElementById(docName).remove();
    document.getElementById(`filter-doc${idx}`).remove();
  
    // get the current summary for this state
    let currObj_sub = submittedSummary.find((o) => o.state_id === idx);
    // submit the data to the server to be logged
    logInteraction("json_example_delete", JSON.stringify(currObj_sub));

    let currObj = sentenceArray.find((o) => o.document_id === targetDoc);
    currObj.submitted.forEach((elem) => {
      if (document.getElementById(elem) !== null) {
        document.getElementById(elem).setAttribute("class", "normal_sentenceSbert");
      }
    });

    currObj.submitted = [];
    submittedSummary = submittedSummary.filter(function (obj) {
      return obj.state_id !== idx;
    });

    if (currentLabel === targetDoc) {
      submitButton.removeAttribute("disabled");
      $("#submitSummary").text("Submit Summary");
      $("#subupButton").tooltip('dispose').attr('data-bs-original-title', "Submit your summary").tooltip();
    }

    if (Object.keys(submittedSummary).length < 2) {
      learnSummaryButton.setAttribute("disabled", "disabled");
      dropdown_output.setAttribute("disabled", "disabled");
    }

    if(Object.keys(submittedSummary).length == 0) {
      $('#summaryWarn').show();
    }

    window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));
    window.localStorage.setItem("submittedSummary", JSON.stringify(submittedSummary));
    disableOldSummary();
  }

  // function that generates the ILP bounds used by SuDocu from the current batch of submitted summaries. 
  $("#button_learnSummary").click(function () {
    $(".warnMes2").attr("style", "display: none");
    $(".subHeader").css("background-color", "#D66420");

    if (Object.keys(submittedSummary).length < 2) {
      alert("Please give at least two example summaries!");
      // $("#button_learnSummary").popover("hide");
      return;
    } else {
      // $("#button_learnSummary").popover("toggle");
      setTimeout(function () {
        // $("#button_learnSummary").popover("hide");
      }, 2000);
    }

    let submittedSummary_server = JSON.parse(JSON.stringify(submittedSummary));
    for (let i = 0; i < submittedSummary_server.length; i++) {
      for (let j = 0; j < submittedSummary_server[i].sentence_ids.length; j++) {
        let reformattedId = parseInt(
          submittedSummary_server[i].sentence_ids[j].substring(6)
        );
        submittedSummary_server[i].sentence_ids[j] = reformattedId;
      }
    }

    // submit the data to the server to be logged
    logInteraction("json_learn_summary", JSON.stringify(submittedSummary_server));

    bounds = [];
    $.ajax({
      url: url_prefix + "learn_summarization",
      async: true,
      type: "POST",
      data: { example: JSON.stringify(submittedSummary_server) },
      beforeSend: function () {
        document.getElementById("generated").innerHTML = "";
        $("#outputDocumentSelector").prop("selectedIndex", 0);
        $("#loaderSbert").show();
        $("#loader_background").show();
      },
      success: function (response) {
        $("#loaderSbert").hide();
        $("#loader_background").hide();
        bounds = response;
        dropdown_output.removeAttribute("disabled");

        window.localStorage.setItem("bounds", JSON.stringify(bounds));

        for (let i = 0; i < bounds.length; i++) {
          // push variables to track changes
          modifiedTopicConstraints.push(false);
        }
      },
    });
  });

  // video modal stuff
  $("#tutorial").click(function () {
    document.getElementById("tutorialVideo").pause();
  });
  $("#tutorialVideo").on("click", function (e) {
    e.preventDefault();
  });

  $("#watchTutorial").click(function () {
    document.getElementById("tutorialVideo").play();
  });


  // gets the most relevant keywords for each topic w.r.t. an underlying state doc or all of the documents
  //     which are saved in a file on the server
  function populateTopicKeywords(idx) {
    $.ajax({
      url: url_prefix + "get_topic_keywords?state_id=" + idx,
      async: true,
      type: "GET",
      dataType: "json",
      success: function (data) {
        let topic_lines = data.topics

        keywordInfo = data.topics
        window.localStorage.setItem("keywordInfo", JSON.stringify(keywordInfo));

        for (let i = 0; i < topic_lines.length; i++) {
          let topic_id = topic_lines[i].topic_id

          let topic_name_id = `#topic${i}_name span`;
          let collapse_id = `#collapse${topic_id}`;
          //messy one liner that adds the top 3 keywords without removing the down arrow div.
          $(topic_name_id).text(topic_lines[i].keywords.split(", ").slice(0, 3).join(', '));
          $(collapse_id).text(topic_lines[i].keywords.split(", ").slice(3, topic_lines[i].keywords.split(", ").length).join(', '));
        }
      },
    });
  }

  // helper function that parses through the "submitted" summaries to format
  //    them into the form required by the server
  function makeExampleSummaries() {
    // extract the example summaries
    let submittedSummary_server = JSON.parse(JSON.stringify(submittedSummary));
    for (let i = 0; i < submittedSummary_server.length; i++) {
      for (let j = 0; j < submittedSummary_server[i].sentence_ids.length; j++) {
        let reformattedId = parseInt(
          submittedSummary_server[i].sentence_ids[j].substring(6)
        );
        submittedSummary_server[i].sentence_ids[j] = reformattedId;
      }
    }

    return submittedSummary_server;
  }

  // function to randomly generate an ID for users
  function makeRandomId() {
    var text = "";
    var possible =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 8; i++)
      text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
  }

  // log an interaction. Content is a json contains the content of the interaction
  //     type is a string indicating the type of interaction:
  // Replace with Firebase
  function logInteraction(type, content) {
    if (recordInteractions == true) {
      var dt = new Date();
      var utcDate = dt.toUTCString();
      let str = userID + "," + utcDate + "," + type + "," + content + "\n";
      console.log(str)
      // window.localStorage.setItem("data_interactions", [])
      if (data_interactions == null) {
        data_interactions = []
      } 
      data_interactions.push(str);
      window.localStorage.setItem("data_interactions", JSON.stringify(data_interactions));
      writeUserData(db, userID, "data_interactions", window.localStorage.getItem("data_interactions"))
    }
  }

  // dumps all saved user-interactions + final state of SuDocu to server
  //     TODO split up into separate dumps for different types of interactions
  function dumpAllUserInteraction() {
    if (recordInteractions == true) {
      $.ajax({
        url: url_prefix + "log_interaction",
        async: true,
        type: "POST",
        data: {
          user_id: userID,
          content: JSON.stringify(data_interactions)
        }
      });
    }
    window.localStorage.setItem("dumped_data", 1)
    window.localStorage.removeItem("data_interactions");
    window.localStorage.removeItem("bounds");
    window.localStorage.removeItem("data_states");
    window.localStorage.removeItem("data_sentences");
    window.localStorage.removeItem("sentenceArray");
    window.localStorage.removeItem("submittedSummary");
    window.localStorage.removeItem("currentLabel");
    window.localStorage.removeItem("prevLabel");

  }

  // initialize local storage to hold interactions for this user
  function initialize_localStorage() {
    window.localStorage.setItem("intilized", 1); 
    userID = makeRandomId(); // make a userID - TODO replace with call to server to also do sudocu or sbert. i.e. server call to 1) get id and 2) assign either SuDocu or SBERT first
    window.localStorage.setItem("userID_sus", userID);
  }

  // function to load state of current study objective (i.e. the specific task they where on)
  function load_LocalStorage() {
    userID = window.localStorage.getItem("userId");
    if (window.localStorage.getItem("dumped_data") === null) {
      data_interactions = JSON.parse(window.localStorage.getItem("data_interactions"));
    } else {
      window.localStorage.removeItem("dumped_data");
    }
  }

});
