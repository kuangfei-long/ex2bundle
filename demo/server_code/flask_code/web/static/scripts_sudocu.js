import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-app.js";
import { getDatabase, ref, set, get, query, onValue } from "https://www.gstatic.com/firebasejs/9.6.3/firebase-database.js";

let url_prefix = "http://127.0.0.1:5000/";
$(document).ready(function () {
  let nTopics = 10;
  let bounds = [];                   // list to hold the generated ILP topic score constraint bounds used by SuDocu
  let data_states = [];              // list of the various state names
  let data_sentences = [];           // list of sentences for currently displayed state doc
  let sentenceArray = [];            // list of sentence used to display current state doc
  let submittedSummary = [];         // list of example summaries submitted by the user
  let keywordInfo = [];              // list containing a history of keyword searches
  let defaultKeywords = {};          // default keywords
  let modifiedKeywords = {};         // modified keywords 
  let exampleSumModifiedKeywords={}; // modified keywords from example summaries
  let currentLabel = "";             // the label (name) of the doc currently selected doc in the Input section
  let prevLabel = "";                // label of the previously selected doc
  var userID = localStorage.getItem("userId");
  let first_gen = true;

  // stuff for relaxation algorithms
  let center_offsets = [];
  let bound_offsets = [];
  let center_slopes = [];
  let bound_slopes = [];
  let r_maxs = [];
  let r_min = 0.1;
  let prev_slider_values = [];
  let stable_bounds = [];
  
  let submitButton = document.getElementById("submitSummary");
  let learnSummaryButton = document.getElementById("button_learnSummary");
  let dropdown_input = document.getElementById("inputDocumentSelector");
  let dropdown_output = document.getElementById("outputDocumentSelector");

  // list to hold JSONS for all user interactions
  let data_interactions = []
  
  var recordInteractions = true;
  let modifiedTopicConstraints = [];

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
      set(ref(db, 'users/' + userId + '/SuDoCuTask/' + question), {
        answer : answer
      });
  }
  
  //Check if user has visited the page
  if (window.localStorage.getItem("intilized") === null) {
    initialize_localStorage();
  } else {
    // load_LocalStorage();
  }

  //disable buttons
  submitButton.setAttribute("disabled", "disabled");
  learnSummaryButton.setAttribute("disabled", "disabled");
  dropdown_output.setAttribute("disabled", "disabled");
  
  $(".highlightAllButton").prop("disabled", true);
  $("#toggleKeywordsButton").prop("disabled", true);
  $(".slider").prop('disabled', true);
  $(".btn.btn-default").prop('disabled', true);
  $("#button_learnSummary").tooltip();
  //complete task button
  $("#button_completeTask").click(function() {
    $(".modal-title").text("Finish Confirmation");
    $(".modal-body").text("Are you sure you want to complete the task?");
    $('#exampleModal').modal("toggle");
    $("#exampleModal").on("click",".btn.btn-secondary", function(){
      dumpAllUserInteraction(); //Data goes to local storage and dump data to the server
      location.href = './postTask-systemU'
    });
    $("#prim").hide();
  })

  let buttonStorage = {
    "undo": ['0,0,0,0,0,0,0,0,0,0'],
    "redo": [],
    "reset": [0,0,0,0,0,0,0,0,0,0]
  };
  //enable the state summary output
  function enableStateOutput(warningMessage) { //pick a warning message to disable
    $("#fafaApply").prop('disabled', true);

    $("#toggleKeywordsButton").css("background-color", "#347F90");

    $("#outputDocumentSelector").prop('disabled', false);
    $(warningMessage).attr("style", "display: none");
    $(".subHeader").css("background-color", "#347F90");
    $(".generatedDoc").css("border-color", "#347F90");
    $(".generatedDoc").css("color", "black");
  }

  //disable the state summary output
  function disableStateOutput(warningMessage) { //pick a warning message to enable

    $("#toggleKeywordsButton").css("background-color", "#8f8f8f");
    // $("#toggleKeywordTooltip").tooltip('show');
    $('#toggleKeywordTooltip').tooltip();
    $("#toggleKeywordTooltip").tooltip('hide')
    .attr('data-bs-original-title', "Show default topic keywords")
    .tooltip('dispose')
    .tooltip('show');

    $("#outputDocumentSelector").prop('disabled', true);
    $(warningMessage).prop("style", "display: flex");
    if(warningMessage === ".warnMes2") {
        $(warningMessage).prop("style", "display: flex; margin-top: 10px; margin-left: auto; margin-right: 0;");
    }
    $(".subHeader").css("background-color", "#8f8f8f");
    $(".generatedDoc").css("border-color", "#8f8f8f");
    $(".generatedDoc").css("color", "#8f8f8f");
  }

  //disable topic importance section, reset sliders to 0
  function disableOldTopicImportance() {
    let reset = buttonStorage['reset'];
    for(let i = 0; i < reset.length; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      slider.value = `${reset[i]}`;
      topicSliderColor(i)
    }

    $("#mainHeaderTopic").css("background", "#8f8f8f");

    $("#toggleKeywordsButton").css("background-color", "#8f8f8f");
    $('#toggleKeywordTooltip').tooltip();
    // $('#toggleKeywordTooltip').tooltip("destroy");

    $(".highlightAllButton").css("border-color", "#8f8f8f");
    $(".highlightAllButton").css("background-color", "white");
    $(".highlightAllButton").prop("disabled", true);

    $(".slider").css("border-color", "#8f8f8f");
    $(".slider").css("background", "white");
    $(".slider").removeClass('sliderEnable');
    $(".slider").prop('disabled', true);

    $("#outputDocumentSelector").prop("disabled", true);
    $(".btn.btn-default").prop('disabled', true);
    $("#generated").children().remove();
    $("#outputDocumentSelector").prop("selectedIndex", 0);
    enableStateOutput(".warnMes");
    disableStateOutput(".warnMes2");
    if(Object.keys(submittedSummary).length < 2) {
      $(".warnMes2 #warnMesText").text("Please submit at least 2 example summaries and analyze your changes.")
    } else {
      $(".warnMes2 #warnMesText").text("Please analyze your changes.")
    }
    newPopulateTopicKeywords(0); //.
  }

  //change topic slider color
  function topicSliderColor(i) {
    var val = (($(`#topic_${i}_slider`).val() - $(`#topic_${i}_slider`).attr('min')) / ($(`#topic_${i}_slider`).attr('max') - $(`#topic_${i}_slider`).attr('min')))*100;
    var val1 = Math.min(val, 50);
    var val2 = Math.max(val, 50);
    // console.log("val1 color", val1)
    // console.log("val2 color", val2)
    $(`#topic_${i}_slider`).css('background', `linear-gradient(to right, white 0%, white ${val1}%, darkgrey ${val1}%, darkgrey 50%, #347F90 50%, #347F90 ${val2}%, white ${val2}%, white 100%)`)
  }

  function unclickHighlightButtons() {
    $(".highlightAllButton").prop("disabled", true);
    $(".highlightAllButton").prop("disabled", false);
    $(".highlightAllButton").css("background-color", "white");
    let instance = new Mark(".generatedDoc");
    let instance2 = new Mark(".summaryText");
    instance.unmark();
    instance2.unmark();
  }

  // functionality for clicking the apply button
  $('#fafaApply').click(function() {
    buttonStorage['redo'] = []
    $('#fafaRedo').prop('disabled', true);

    unclickHighlightButtons();

    $('#fafaUndo').prop('disabled', false);
    enableStateOutput(".warnMes");

    let apply = []
    for(let i = 0; i < 10; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      apply.push(slider.value)
    }

    buttonStorage["undo"].push(apply.join(','));

    let select = document.getElementById('outputDocumentSelector');
    if(select.options[select.selectedIndex].value !== '0') {
      getSummAjax_NoRelax();
      // getSummAjax();
      // let topic_currentLabel = $("#outputDocumentSelector").val();
      // let idx = parseInt(topic_currentLabel.substring(14));
    }
  })

  // functionality for clicking the undo button
  $('#fafaUndo').click(function() {
    unclickHighlightButtons();

    enableStateOutput(".warnMes");
    buttonStorage['redo'].push(buttonStorage['undo'].pop());
    $('#fafaRedo').prop('disabled', false);

    let undo = buttonStorage['undo'][buttonStorage['undo'].length-1].split(',');
    let reset = buttonStorage['reset'];

    for(let i = 0; i < reset.length; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      slider.value = `${undo[i]}`;
      topicSliderColor(i);
    }

    let select = document.getElementById('outputDocumentSelector');
    if(select.options[select.selectedIndex].value !== '0') {
      // getSummAjax();
      getSummAjax_NoRelax();
    }

    if(buttonStorage['undo'].length <= 1) {
      $('#fafaUndo').prop('disabled', true);
    }
  })

  // functionality for clicking the redo button
  $('#fafaRedo').click(function() {
    unclickHighlightButtons();

    enableStateOutput(".warnMes");
    let redo = buttonStorage['redo'][buttonStorage['redo'].length-1].split(',');

    for(let i = 0; i < redo.length; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      slider.value = `${redo[i]}`;
      topicSliderColor(i)
    }
    buttonStorage['undo'].push(buttonStorage['redo'].pop());
    $('#fafaUndo').prop('disabled', false);

    let select = document.getElementById('outputDocumentSelector');
    if(select.options[select.selectedIndex].value !== '0') {
      // getSummAjax();
      getSummAjax_NoRelax();
    }

    if(buttonStorage['redo'].length < 1) {
      $('#fafaRedo').prop('disabled', true);
    }
  })

  // functionality for clicking the reset button
  let ffr = 0
  $("#fafaReset").click(function() {
    unclickHighlightButtons();

    ffr = 1
    $(".modal-title").text("Are you sure you want to reset the sliders?");
    $(".modal-body").text("The sliders will reset to 0.");
    $('#exampleModal').modal("toggle");
    $("#exampleModal").on("click",".btn.btn-secondary", function(){
      if(ffr == 1){
        ffr = 0;
        $("#fafaReset").prop("disabled", true);
        enableStateOutput(".warnMes");
        let reset = buttonStorage['reset'];
        for(let i = 0; i < reset.length; i++) {
          let slider = document.getElementById(`topic_${i}_slider`);
          slider.value = 0;
          topicSliderColor(i)
        }
        buttonStorage['undo'] = ['0,0,0,0,0,0,0,0,0,0'];
        buttonStorage['redo'] = [];
        $('#fafaUndo').prop('disabled', true);
        $('#fafaRedo').prop('disabled', true);

        let select = document.getElementById('outputDocumentSelector');
        if(select.options[select.selectedIndex].value !== '0') {
          // getSummAjax();
          getSummAjax_NoRelax();
        }
      }
      ffr = 0;
      $('#exampleModal').modal("toggle");
    });
    $(".btn.btn-primary").show(); 
    $("#exampleModal").on("click",".btn.btn-primary", function(){
      $('#exampleModal').modal("toggle");
      ffr = 0;
    });
  })


  // this ajac request initially populates the input document selection dropdown. 
  $.ajax({
    url: url_prefix + "get_states_sudocu",
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

  newPopulateTopicKeywords(0); 

  // user-feedback popovers for various buttons
  $("#genSumInfoIcon").popover("enable");
  $("#sumSelectorInfoIcon").popover("enable");
  $("#exSumInfoIcon").popover("enable");
  $("#PaQLInfoIcon").popover("enable");
  $('.slider').popover("enable");
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
      document.getElementById("docContent").appendChild(sampleContent);
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
          .setAttribute("class", "normal_sentence");
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
        $("#loader").show();
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
          span.setAttribute("class", "normal_sentence");
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
              .setAttribute("class", "selected");
          }
        }

        document.getElementById("searchInput").value = "";
      },
      complete: function () {
        $("#loader").hide();
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

  let selectedState = "None";
  $(".generatedDoc").hide();

  $('.slider').change(function () {
    disableStateOutput(".warnMes");
    //subheader grey, textbox grey
    let vals = [];
    for(let i = 0; i < 10; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      vals.push(slider.value);
    }
    
    let len = buttonStorage['undo'].length;

    if(vals.join(',') === buttonStorage['undo'][len - 1]) {
      enableStateOutput(".warnMes");
    } else {
      $("#fafaApply").prop('disabled', false);
    }
    
    if(vals.join(',') === buttonStorage['reset'].join(',')) {
      $("#fafaReset").prop('disabled', true);
    } else {
      $("#fafaReset").prop('disabled', false);
    }
  })
  // function to actually generate a summary. 
  // checks if bounds have been modified. If so, use modified bounds, otherwise use the default learned bounds
  $('#outputDocumentSelector').change(function () {
    // always need to run this again when running for a new state
    // TODO: might want to revist to be more intelligent
    // ISSUE:    how to carry slider changes between states
    //           currently, always reset sliders on state change
    // IDEA:     cache slider changes on state change, then -> solve with alg. 1, reseting slider alg. values as / if needed
    //             after, then resolve with cached slider positions
    // first_gen = true;
    if (first_gen == false) {
      getSumSliderValsStateChange();
    } else {
      // getSummAjax();
      getSummAjax_NoRelax();
    }

    $(".slider").prop('disabled', false);
    $('.slider').on("input", function () {
      var val = (($(this).val() - $(this).attr('min')) / ($(this).attr('max') - $(this).attr('min')))*100;
      var val1 = Math.min(val, 50);
      var val2 = Math.max(val, 50);
      $(this).css('background', `linear-gradient(to right, white 0%, white ${val1}%, darkgrey ${val1}%, darkgrey 50%, #347F90 50%, #347F90 ${val2}%, white ${val2}%, white 100%)`)
    });
    // $(".slider").css("background", "#347F90");
    $(".slider").css("border-color", "#347F90");
    $(".slider").addClass('sliderEnable');

    function check() {
      if ($('.generatedDoc').text() === "") {
          return setTimeout(check, 1000);
      }

      let genSummary = [];
      genSummary.push($(".generatedDoc").text());
      modifiedKeywords = exampleSumModifiedKeywords;
      newPopulateTopicKeywords(1, genSummary);
    }
  
    check();

    let topic_currentLabel = $(this).val();
    let idx = parseInt(topic_currentLabel.substring(14));
    $("#button_completeTask").prop('disabled', false);
  });


  function getSumSliderValsStateChange() {
    // cache old values
    let temp_slides = []
    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
      temp_slides.push(slider_val)
    }
    
    // solve as if this is the first gen for the state
    first_gen = true;
    // getSummAjax_Sync();
    getSummAjax_NoRelax_Sync();
    // stable_bounds = bounds;

    // put the slider values back to the apperoperiate positions
    for (let i = 0; i < bounds.length; i++) {
      let topicId = i.toString(10);
      let slider = document.getElementById(`topic_${topicId}_slider`);
      slider.value = `${temp_slides[i]}`
      if (temp_slides[i] != 0) {
        modifiedTopicConstraints[i] = true;
        var val = (($(`#topic_${i}_slider`).val() - $(`#topic_${i}_slider`).attr('min')) / ($(`#topic_${i}_slider`).attr('max') - $(`#topic_${i}_slider`).attr('min')))*100;
        var val1 = Math.min(val, 50);
        var val2 = Math.max(val, 50);
        $(`#topic_${i}_slider`).css('background', `linear-gradient(to right, white 0%, white ${val1}%, darkgrey ${val1}%, darkgrey 50%, #347F90 50%, #347F90 ${val2}%, white ${val2}%, white 100%)`)  
      }
      prev_slider_values[i] = 0;
    }

    // now resolve to try and get back the correct slider positions
    //    using the newly created / cached slider alg values for this state
    // getSummAjax();
    getSummAjax_NoRelax();
  }

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
    // add in the bounds
    // modified values use the slider results, otherwise use the learned bounds
    let summary_bounds = []
    let slider_val_diffs = []
    let slider_vals = []

    generated_summary_log['modified_bounds'] = 0;
    //When user modifies slider changer value
    //Build data structure then turned to JSON 
    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      if (modifiedTopicConstraints[i] == true) {
        generated_summary_log['modified_bounds'] = 1;
        let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
        let temp_bounds = get_bounds_from_importance_scores(i, slider_val)
        summary_bounds.push(temp_bounds);
        // TODO: note, currently prev_slider_values[] is always zero, this avoids regressing back to in-feasbile state
        //     COULD try and make it w.r.t. previously working slider values, would need to return from SuDocu
        slider_val_diffs.push(prev_slider_values[i] - slider_val);
      } else {
        summary_bounds.push(bounds[i]);
        slider_val_diffs.push(0.0)
      }
    }

    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
      slider_vals.push(slider_val)
    }
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
        bounds: JSON.stringify(summary_bounds),
        stable_bounds: JSON.stringify(stable_bounds),
        first_gen: first_gen,
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
        center_slopes: JSON.stringify(center_slopes),
        center_offsets: JSON.stringify(center_offsets),
        bound_slopes: JSON.stringify(bound_slopes),
        bound_offsets: JSON.stringify(bound_offsets),
        r_maxs: JSON.stringify(r_maxs),
        slider_diffs: JSON.stringify(slider_val_diffs),
        slider_vals: JSON.stringify(slider_vals),
        prev_slider_vals: JSON.stringify(prev_slider_values)
      },
      //show loading
      beforeSend: function () {
        $("#loader").show();
        $("#loader_background").show();
        $("#wait").text("Please Wait.");
        $("#wait").show();
        t1;
        t2;
      },
      //remove loading
      success: function (data) {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
        $("#loader").hide();
        $("#loader_background").hide();
        $("#wait").text("Please Wait.");
        $("#wait").hide();
        let summary = data.summary;
        let default_summ = data.default;
        let summ_indicies = data.summary_indicies
        let relaxed_bounds = data.bounds

        let slider_values = []
        for (let i = 0; i < bounds.length; i++) {
          let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
          slider_values.push(slider_val)
        }

        generated_summary_log['state_id'] = docId
        generated_summary_log['state_name'] = stateName
        generated_summary_log['slider_values'] = slider_values
        generated_summary_log['bounds'] = summary_bounds
        generated_summary_log['relaxed_bounds'] = relaxed_bounds
        generated_summary_log['examples'] = submittedSummary_server
        generated_summary_log['summary_indicies'] = summ_indicies
        generated_summary_log['default_summ'] = default_summ
        
        logInteraction("json_generate_summary", JSON.stringify(generated_summary_log));

        // if this is the first time we generated a summary from these examples
        if (first_gen) {
          prev_slider_values = [];
          first_gen = false;
          bounds = relaxed_bounds;
          compile_bounds_stats();
          loadTopicSliders();

          // Unsure if this is useful still?
          stable_bounds = relaxed_bounds;
          // TODO: consider how we want to do this
          for (let i=0; i < bounds.length; i++) {
            prev_slider_values.push(0);
          }
        } else {
          prev_slider_values = data.slider_vals;
        }
        let summaryDiv = "#learnedSummary" + docId.toString(10);
        document.getElementById("learnedSummary" + docId.toString(10)).innerHTML = summary;

        if (default_summ == true) {
          $(".modal-title").text("Topic Score Constraints too strict!");
          $(".modal-body").text("No solution could be found and a default summary was returned.");
          $('#exampleModal').modal("toggle");
          $("#exampleModal").on("click",".btn.btn-secondary", function(){
            $('#exampleModal').modal("toggle");
          });
          $("#prim").hide();
        }
      },
    });
  }

  function getSummAjax_Sync() {
    $(".generatedDoc").hide();
    // get the value of the currently selected item
    let select = document.getElementById('outputDocumentSelector');
    let currentLearnedLabel = select.options[select.selectedIndex].value;
    let stateName = select.options[select.selectedIndex].textContent;
    // get the name of the selected state from the dropdown
    selectedState = $("#outputDocumentSelector option:selected").text();

    //First time select statement to generate
    // if (showExplanation == false) {
    //   explanationWindow.style.display = "block";
    //   explanationWindow.style.visibility = "visible";
    //   window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    //   showExplanation = true;
    // } 
    
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
    // add in the bounds
    // modified values use the slider results, otherwise use the learned bounds
    let summary_bounds = []
    let slider_val_diffs = []
    let slider_vals = []


    generated_summary_log['modified_bounds'] = 0;
    //When user modifies slider changer value
    //Build data structure then turned to JSON 
    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      if (modifiedTopicConstraints[i] == true) {
        generated_summary_log['modified_bounds'] = 1;
        let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
        let temp_bounds = get_bounds_from_importance_scores(i, slider_val)
        summary_bounds.push(temp_bounds);
        slider_val_diffs.push(prev_slider_values[i] - slider_val);
      } else {
        summary_bounds.push(bounds[i]);
        slider_val_diffs.push(0.0)
      }
    }

    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
      slider_vals.push(slider_val)
    }
    $.ajax({
      url: url_prefix + "get_summary",
      async: false,
      type: "POST",
      data: {
        user_id: userID,
        bounds: JSON.stringify(summary_bounds),
        stable_bounds: JSON.stringify(bounds),
        first_gen: first_gen,
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
        center_slopes: JSON.stringify(center_slopes),
        center_offsets: JSON.stringify(center_offsets),
        bound_slopes: JSON.stringify(bound_slopes),
        bound_offsets: JSON.stringify(bound_offsets),
        r_maxs: JSON.stringify(r_maxs),
        slider_diffs: JSON.stringify(slider_val_diffs),
        slider_vals: JSON.stringify(slider_vals),
        prev_slider_vals: JSON.stringify(prev_slider_values)
      },
      //show loading
      beforeSend: function () {
        $("#loader").show();
        $("#loader_background").show();
      },
      //remove loading
      success: function (data) {
        let summary = data.summary;
        let default_summ = data.default;
        let summ_indicies = data.summary_indicies
        let relaxed_bounds = data.bounds


        let slider_values = []
        for (let i = 0; i < bounds.length; i++) {
          let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
          slider_values.push(slider_val)
        }
        
        generated_summary_log['state_id'] = docId
        generated_summary_log['state_name'] = stateName
        generated_summary_log['slider_values'] = slider_values
        generated_summary_log['bounds'] = summary_bounds
        generated_summary_log['relaxed_bounds'] = relaxed_bounds
        generated_summary_log['examples'] = submittedSummary_server
        generated_summary_log['summary_indicies'] = summ_indicies
        generated_summary_log['default_summ'] = default_summ
        
        logInteraction("json_generate_summary", JSON.stringify(generated_summary_log));


        // if this is the first time we generated a summary from these examples
        if (first_gen) {
          first_gen = false;
          bounds = relaxed_bounds;
          stable_bounds = relaxed_bounds;
          compile_bounds_stats();
          loadTopicSliders();
        }

        prev_slider_values = slider_vals;
      },
    });
  }


  function getSummAjax_NoRelax() {
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

    // add in the bounds
    // modified values use the slider results, otherwise use the learned bounds
    let summary_bounds = []


    generated_summary_log['modified_bounds'] = 0;
    //When user modifies slider changer value
    //Build data structure then turned to JSON 
    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      if (modifiedTopicConstraints[i] == true) {
        generated_summary_log['modified_bounds'] = 1;
        let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
        let temp_bounds = get_bounds_from_importance_scores(i, slider_val)
        summary_bounds.push(temp_bounds);
        // TODO: note, currently prev_slider_values[] is always zero, this avoids regressing back to in-feasbile state
        //     COULD try and make it w.r.t. previously working slider values, would need to return from SuDocu
      } else {
        summary_bounds.push(bounds[i]);
      }
    }

    let t1 = window.setTimeout(() => {
      $("#wait").text("Taking longer than expected.");
    }, 4000);
    let t2 = window.setTimeout(() => {
      $("#wait").text("Just a little longer.");
    }, 8000);
    $.ajax({
      url: url_prefix + "get_summary_initial",
      async: true,
      type: "POST",
      data: {
        user_id: userID,
        bounds: JSON.stringify(summary_bounds),
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
      },
      //show loading
      beforeSend: function () {
        $("#loader").show();
        $("#loader_background").show();
        $("#wait").show();
        t1;
        t2;
      },
      //remove loading
      success: function (data) {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
        $("#loader").hide();
        $("#loader_background").hide();
        $("#wait").text("Please Wait.");
        $("#wait").hide();
        let summary = data.summary;
        let summ_indicies = data.summary_indicies

        let slider_values = []
        for (let i = 0; i < bounds.length; i++) {
          let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
          slider_values.push(slider_val)
        }

        generated_summary_log['state_id'] = docId
        generated_summary_log['state_name'] = stateName
        generated_summary_log['slider_values'] = slider_values
        generated_summary_log['bounds'] = summary_bounds
        generated_summary_log['examples'] = submittedSummary_server
        generated_summary_log['summary_indicies'] = summ_indicies
        
        logInteraction("json_generate_summary_initial", JSON.stringify(generated_summary_log));

        if (summary == "none") {
          // first call the solver again
          getSummAjax();
        } else {
          document.getElementById("learnedSummary" + docId.toString(10)).innerHTML = summary;
        }
      },
    });
  }


  function getSummAjax_NoRelax_Sync() {
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
    // add in the bounds
    // modified values use the slider results, otherwise use the learned bounds
    let summary_bounds = []


    generated_summary_log['modified_bounds'] = 0;
    //When user modifies slider changer value
    //Build data structure then turned to JSON 
    for (let i = 0; i < bounds.length; i++) {
      // if the original bounds that have been generated after clicking analyze have been modified at all
      if (modifiedTopicConstraints[i] == true) {
        generated_summary_log['modified_bounds'] = 1;
        let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
        let temp_bounds = get_bounds_from_importance_scores(i, slider_val)
        summary_bounds.push(temp_bounds);
        // TODO: note, currently prev_slider_values[] is always zero, this avoids regressing back to in-feasbile state
        //     COULD try and make it w.r.t. previously working slider values, would need to return from SuDocu
      } else {
        summary_bounds.push(bounds[i]);
      }
    }

    let t1 = window.setTimeout(() => {
      $("#wait").text("Taking longer than expected.");
    }, 4000);
    let t2 = window.setTimeout(() => {
      $("#wait").text("Just a little longer.");
    }, 8000);
    $.ajax({
      url: url_prefix + "get_summary_initial",
      async: false,
      type: "POST",
      data: {
        user_id: userID,
        bounds: JSON.stringify(summary_bounds),
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
      },
      //show loading
      beforeSend: function () {
        $("#loader").show();
        $("#loader_background").show();
        $("#wait").show();
        t1;
        t2;
      },
      //remove loading
      success: function (data) {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
        $("#loader").hide();
        $("#loader_background").hide();
        $("#wait").text("Please Wait.");
        $("#wait").hide();
        let summary = data.summary;
        let summ_indicies = data.summary_indicies


        let slider_values = []
        for (let i = 0; i < bounds.length; i++) {
          let slider_val = parseInt(document.getElementById("topic_" + (i).toString(10) + "_slider").value);
          slider_values.push(slider_val)
        }

        generated_summary_log['state_id'] = docId
        generated_summary_log['state_name'] = stateName
        generated_summary_log['slider_values'] = slider_values
        generated_summary_log['bounds'] = summary_bounds
        generated_summary_log['examples'] = submittedSummary_server
        generated_summary_log['summary_indicies'] = summ_indicies
        
        logInteraction("json_generate_summary_initial", JSON.stringify(generated_summary_log));

        if (summary == "none") {
          // first call the solver again
          getSummAjax_Sync();

          // then inform user
          // alert("Performing Relaxation");
        } else {
          document.getElementById("learnedSummary" + docId.toString(10)).innerHTML = summary;
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
      curr.setAttribute("class", "normal_sentence");
      const index = currObj.submitted.findIndex((item) => item === currentId);
      if (index > -1) {
        currObj.submitted.splice(index, 1);
      }
    } else if (!sentenceIsSelected(currentId)) {
      curr.setAttribute("class", "selected");
      currObj.selected.push(currentId);
    } else if (sentenceIsSelected(currentId)) {
      curr.setAttribute("class", "normal_sentence");
      const index = currObj.selected.findIndex((item) => item === currentId);
      if (index > -1) {
        currObj.selected.splice(index, 1);
      }
    }
    $(".selected").attr("title", "click to unselect the sentence");
    $(".normal_sentence").attr("title", "click to select the sentence");

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
    
    // this work displays the relevent sentences in the doc page
    for (let i = 0; i < spanArray.length; i++) {
      if(spanArray[i].textContent == " " || spanArray[i].textContent.toUpperCase().indexOf(filter) > -1) {
      // if (filter === "" || spanArray[i].textContent.toUpperCase().replace(/[^a-zA-Z ]/g, "").split(" ").indexOf(filter) > -1) {
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
        $("#prim").hide();
        return;
      } else {
        $("#submitSummary").popover("toggle");
        setTimeout(function () {
          $("#submitSummary").popover("hide");
        }, 2000);
      }
      for (let i = 0; i < currObj.selected.length; i++) {
        currObj.submitted.push(currObj.selected[i]);
        document
          .getElementById(currObj.submitted[i])
          .setAttribute("class", "selected");
      }
      currObj.selected = [];
      let idx = parseInt(currentLabel.substring(3));
  
      let docName = ""
  
      for (let j = 0; j < data_states.length; j++) {
        if (data_states[j].state_id == idx) {
          docName = data_states[j].state_name;
        }
      }
  
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
      $(".summaryStates").append(filterBtn);

      let minimizeBtn = document.createElement("div");
      minimizeBtn.setAttribute("class", "minimize-button");
      minimizeBtn.setAttribute("id", "minimize-" + currentLabel);
      minimizeBtn.setAttribute("title", "Remove this summary");
      minimizeBtn.onclick = filterSubmission;
      minimizeBtn.innerHTML = "&#8722";
      
      let modalWasClosed = 0;
      let closeBtn = document.createElement("div");
      closeBtn.setAttribute("class", "close-button");
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
        instance.unmark({
          "accuracy": {
            "value": "exactly",
            "limiters": [",",".","'",";",":","[","]","(",")"]
          },
          ignorePunctuation: ["'"],
          "separateWordSearch": false,
        });
        
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
          .setAttribute("class", "selected");
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
        $("#prim").hide();
        return;
      }
      currTextBox.textContent = content;

      window.localStorage.setItem("sentenceArray", JSON.stringify(sentenceArray));
    }
    
    window.localStorage.setItem("submittedSummary", JSON.stringify(submittedSummary));
    if($(".mainHeaderSuDoCu#mainHeaderTopic").css("background-color") !== "rgb(143, 143, 143)") {
      disableOldTopicImportance();
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
        $(`#filter-${targetDoc}`).css("background", "#347F90");
        $(`#filter-${targetDoc}`).css("color", "white");
        },
        function() {
          $(`#filter-${targetDoc}`).css("background", "white");
          $(`#filter-${targetDoc}`).css("color", "black");
        })
    } else {
      $(`#filter-${targetDoc}`).prop('title', 'Click to unselect tab');
      $(`#${docName}`).show();
      $(`#filter-${targetDoc}`).css("background", "#347F90");
      $(`#filter-${targetDoc}`).css("color", "white");
      $(`#filter-${targetDoc}`).hover(function() {
        $(`#filter-${targetDoc}`).css("background", "white");
        $(`#filter-${targetDoc}`).css("color", "black");},
        function() {
          $(`#filter-${targetDoc}`).css("background", "#347F90");
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
        document.getElementById(elem).setAttribute("class", "normal_sentence");
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
    disableOldTopicImportance();
  }

  // function that generates the ILP bounds used by SuDocu from the current batch of submitted summaries. 
  $("#button_learnSummary").click(function () {
    $(".highlightAllButton").css("border-color", "#347F90");
    $(".highlightAllButton").prop("disabled", false);

    unclickHighlightButtons();
    
    buttonStorage = {
      "undo": ['0,0,0,0,0,0,0,0,0,0'],
      "redo": [],
      "reset": [0,0,0,0,0,0,0,0,0,0]
    };

    enableStateOutput(".warnMes");
    enableStateOutput(".warnMes2");
    $("#fafaRedo").prop('disabled', true);
    $("#fafaUndo").prop('disabled', true);
    $("#fafaApply").prop('disabled', true);
    $("#fafaReset").prop('disabled', true);

    $(".slider").prop('disabled', true);
    let reset = buttonStorage['reset'];
    for(let i = 0; i < reset.length; i++) {
      let slider = document.getElementById(`topic_${i}_slider`);
      slider.value = `${reset[i]}`;
      topicSliderColor(i)
    }
    $(".slider").css("border-color", "#8f8f8f");
    $(".slider").css("background", "white");
    $(".slider").removeClass('sliderEnable');
    $(".slider").prop('disabled', true);

    // $(".slider").prop('disabled', false);
    // $('.slider').on("input", function () {
    //   var val = (($(this).val() - $(this).attr('min')) / ($(this).attr('max') - $(this).attr('min')))*100;
    //   var val1 = Math.min(val, 50);
    //   var val2 = Math.max(val, 50);
    //   $(this).css('background', `linear-gradient(to right, white 0%, white ${val1}%, darkgrey ${val1}%, darkgrey 50%, #347F90 50%, #347F90 ${val2}%, white ${val2}%, white 100%)`)
    // });
    // $(".slider").css("background", "#347F90");
    // $(".slider").css("border-color", "#347F90");
    // $(".slider").addClass('sliderEnable');

    $("#mainHeaderTopic").css("background", "#347F90");

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
        $("#loader").show();
        $("#loader_background").show();
      },
      success: function (response) {
        $("#loader").hide();
        $("#loader_background").hide();
        bounds = response;
        stable_bounds = bounds;
        // dropdown_output.removeAttribute("disabled");

        window.localStorage.setItem("bounds", JSON.stringify(bounds));

        for (let i = 0; i < bounds.length; i++) {
          // push variables to track changes
          modifiedTopicConstraints.push(false);
        }

        // calculate the resulting topic score slider values
        compile_bounds_stats();
        loadTopicSliders();

        // set global var saying we are generating a summary for these
        //    examples for the first time
        first_gen = true;
      },
    });

    let exampleSummaries = [];
    $(".exampleSummaries").children().each(function () {
      exampleSummaries.push($(this).children(".summaryText").text());
    });
    modifiedKeywords = exampleSumModifiedKeywords;
    newPopulateTopicKeywords(1, exampleSummaries);
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

  $("#toggleKeywordsButton").hover(function () {
    if($(".mainHeaderSuDoCu#mainHeaderTopic").css("background-color") !== "rgb(143, 143, 143)") { 
      $(this).css("border-color", "#296f7f");
    }
  }, function () {
    if($(".mainHeaderSuDoCu#mainHeaderTopic").css("background-color") !== "rgb(143, 143, 143)") { 
      $(this).css("border-color", "white");
    }
  });

  //couldnt get mark js unmark to work for specific elements, came up with own version
  //loop through all the spans in the generated summary and unmark all words that have an class (class that determines which topic they belong to)
  function unmarkSpecificWords(num) {
    $('.generatedDoc').each(function () {
      if($(this).children().hasClass(num)) {
        $(this).children(`.${num}`).replaceWith((i, txt) => txt);
      }
    });
    $('.summaryText').each(function () {
      if($(this).children().hasClass(num)) {
        $(this).children(`.${num}`).replaceWith((i, txt) => txt);
      }
    });
  }

  //click to highlight all words in a certain topic
  $(".highlightAllButton").click(function () {
    let instance = new Mark(".generatedDoc");
    let instance2 = new Mark(".summaryText");
    let topic_lines = keywordInfo;
    let topic_id_helper = topic_lines[parseInt($(this).parent().parent().attr('id').slice(19))].keywords;
    let topic_id = [];
    for(let i = 0; i < topic_id_helper.length; i++) {
      topic_id.push(topic_id_helper[i].word);
    }

    let num = $(this).parent().parent().attr('id').slice(19);
    let options = {
      "className": num+1,
      "accuracy": {
        "value": "exactly",
        "limiters": [",",".","'",";",":","[","]","(",")"]
      },
      ignorePunctuation: ["'"],
      "separateWordSearch": false,
    }
    if($(this).css("background-color") == "rgb(255, 255, 255)"){

      $(".highlightAllButton").each(function () {
        if($(this).css("background-color") !== "rgb(255, 255, 255)") {
          $(this).css("background-color", "white");

          let num = $(this).parent().parent().attr('id').slice(19);
          unmarkSpecificWords(num+1);
        }
      });

      $(this).css("background-color", "#347F90");  
      instance.mark(topic_id, options);
      instance2.mark(topic_id, options);
    } else {
      $(this).css("background-color", "white");
      
      //couldnt get mark js unmark to work for specific elements, came up with own version
      //loop through all the spans in the generated summary and unmark all words that have an class (class that determines which topic they belong to)
      unmarkSpecificWords(num+1);
    }
  });

  function newPopulateTopicKeywordsHelper(topic_lines) {
    for (let i = 0; i < topic_lines.length; i++) {
      let topic_id = topic_lines[i].topic_id;
      let topic_name_id = `#topic${topic_id}_name span#words`;
      let collapse_id = `#collapse${topic_id} span#words`;
      //top 3 topic words
      let top3Words = topic_lines[topic_id].keywords.slice(0, 3);
      //the rest of the words when collapsed
      let restOfWords = topic_lines[topic_id].keywords.slice(3, topic_lines[i].keywords.length);
      //append each word as a span
      $(topic_name_id).empty();
      $(collapse_id).empty();
      let instance = new Mark(".generatedDoc");
      let instance2 = new Mark(".summaryText");
      
      let options = {
        "className": topic_id+1,//for some reason mark.js doesnt create classes with the name 0
        "accuracy": {
          "value": "exactly",
          "limiters": [",",".","'",";",":","[","]","(",")"]
        },
        ignorePunctuation: ["'"],
        "separateWordSearch": false,
      }
      for(let j = 0; j < top3Words.length; j++) {
        let top = typeof(top3Words[j].word) !== 'undefined' ? top3Words[j].word : top3Words[j];
        if(top3Words[j].count > 0) {
          $(topic_name_id).append(`<span id='word${j}' style='color: #347F90; font-weight:bold; cursor: pointer;'>` + top + '</span>'); 
        } else {
          $(topic_name_id).append(`<span id='word${j} style='cursor: pointer;'>` + top + '</span>'); 
        }
        
        if(restOfWords.length === 0) {
          if(j+1 !== top3Words.length) {
            $(topic_name_id).append(', ');
          }
        } else {
          $(topic_name_id).append(', ');
        }
        //hover over word in topic importance section
        $(`${topic_name_id} #word${j}`).mouseover(function() {
          //if disabled dont highlight
          if($(".mainHeaderSuDoCu#mainHeaderTopic").css("background-color") !== "rgb(143, 143, 143)") {
            $(this).css("background-color", "#9ACEDA"); 
            //if the current topic highlight button is pressed, dont un/highlight specific words 
            if($(`#topicNamesAndSlider${topic_id} .highlightAll .highlightAllButton`).css("background-color") == "rgb(255, 255, 255)") {
              unmarkSpecificWords(topic_id+1);
              instance.mark($(`${topic_name_id} #word${j}`).text(), options);
              instance2.mark($(`${topic_name_id} #word${j}`).text(), options);
            }
          }
        });

        //no longer hovering
        $(`${topic_name_id} #word${j}`).mouseout(function() {

          $(this).css("background-color", "white");
          if($(`#topicNamesAndSlider${topic_id} .highlightAll .highlightAllButton`).css("background-color") == "rgb(255, 255, 255)") {  
            unmarkSpecificWords(topic_id+1);
          }
        });
      }

      for(let j = 0; j < restOfWords.length; j++) {
        let rest = typeof(restOfWords[j].word) !== 'undefined' ? restOfWords[j].word : restOfWords[j]    
        if(restOfWords[j].count > 0) {
          $(collapse_id).append(`<span id='word${j}' style='color: #347F90; font-weight:bold; cursor: pointer;'>` + rest + '</span>'); 
        } else {
          $(collapse_id).append(`<span id='word${j}' style='cursor: pointer;'>` + rest + '</span>'); 
        }

        if(j+1 !== restOfWords.length) {
          $(collapse_id).append(', ');
        }
        //hover over word in topic importance section
        $(`#collapse${topic_id} span#words #word${j}`).mouseover(function() {
          //if disabled dont highlight
          if($(".mainHeaderSuDoCu#mainHeaderTopic").css("background-color") !== "rgb(143, 143, 143)") {
            $(this).css("background-color", "#9ACEDA"); 
            //if the current topic highlight button is pressed, dont un/highlight specific words 
            if($(`#topicNamesAndSlider${topic_id} .highlightAll .highlightAllButton`).css("background-color") == "rgb(255, 255, 255)") {
              unmarkSpecificWords(topic_id+1);
              instance.mark($(`${collapse_id} #word${j}`).text(), options);
              instance2.mark($(`${collapse_id} #word${j}`).text(), options);
            }
          }
        });
        //no longer hovering
        $(`${collapse_id} #word${j}`).mouseout(function() {
          $(this).css("background-color", "white");  
          if($(`#topicNamesAndSlider${topic_id} .highlightAll .highlightAllButton`).css("background-color") == "rgb(255, 255, 255)") {
            unmarkSpecificWords(topic_id+1);
          }
        });
      }
    }
  }

  function newPopulateTopicKeywords(idx, summaries) {
    $.ajax({
      url: url_prefix + "topic_keyword_appearances",
      async: true,
      type: "POST",
      data: { 
        example: JSON.stringify(summaries),
        modified: idx,
      },
      beforeSend: function () {
        if(typeof(summaries) === "undefined" || summaries.length > 1) { 
          document.getElementById("generated").innerHTML = "";
          $("#outputDocumentSelector").prop("selectedIndex", 0);
        } 
        $("#loader").show();
        $("#loader_background").show();
      },
      success: function (response) {
        let resCopy = structuredClone(response);
        $("#loader").hide();
        $("#loader_background").hide();
        // dropdown_output.removeAttribute("disabled");
        //if we want the unmodified keywords, convert the keyword values to a list (all_states.txt has them set as a string)
        if(idx === 0) {
          for(let i = 0; i< resCopy.length; i++) {
            resCopy[i].keywords = resCopy[i].keywords.split(', ')
          } 
          defaultKeywords = resCopy;
        } else {
          if(summaries.length === 1) {
            modifiedKeywords = exampleSumModifiedKeywords;
            for(let i = 0; i < response.length; i++) {
              resCopy[i].keywords = resCopy[i].keywords.concat(modifiedKeywords[i].keywords);

              //sort the words by most popular
              resCopy[i].keywords.sort(function(a, b) {
                return ((a.count < b.count) ? -1 : ((a.count == b.count) ? 0 : 1));
              }).reverse();

              //remove dupe words
              let uniqueIds = [];
              resCopy[i].keywords = resCopy[i].keywords.filter(element => {
                let isDuplicate = uniqueIds.includes(element.word);
                if (!isDuplicate) {
                  uniqueIds.push(element.word);
                  return true;
                }
                return false;
              }).slice(0, 10);
            }
            modifiedKeywords = resCopy;
          } else {
            modifiedKeywords = resCopy;
            exampleSumModifiedKeywords = resCopy;
          }
        }

        let topic_lines = resCopy;
        keywordInfo = resCopy;
        window.localStorage.setItem("keywordInfo", JSON.stringify(keywordInfo));

        if(typeof(summaries) === "undefined" || summaries.length > 1) {
          newPopulateTopicKeywordsHelper(topic_lines);
        }
        if(typeof(summaries) !== "undefined") {
          if(summaries.length === 1){
            newPopulateTopicKeywordsHelper(topic_lines);
          }
        }
      },
    })
  }

  $('.collapse').on('shown.bs.collapse', function () {
    let parent = $(this).parent()
    $(parent).css({
      // "width": "55%",
      "border-color": "rgba(0,0,0,.125)", 
      "border-width":"1px", 
      "border-style":"solid",
      "border-radius":".25rem",
      "padding-left":"1px",
      "margin-bottom":"1px"
    });
    let button = parent.children()[0]
    $(button).find("#ellipsis").hide();
    parent.children(".btn.btn-primary").css("margin-bottom", "-3.4%");
 });
 $('.collapse').on('hidden.bs.collapse', function () {
  let parent = $(this).parent();
  $(parent).css({
    "min-width": "54%",
    "border": "none",  
    "padding-left":"0",
    "margin-bottom":"1px"
  });

  let button = parent.children()[0]
  $(button).find("#ellipsis").show();
  parent.children(".btn.btn-primary").css("margin-bottom", "3px");
});

  // initializes the topic sliders to their start state 
  function loadTopicSliders() {
    let bound_importance_scores = get_bounds_importance_scores();
    // let reset = [];
    let apply = [];
    for (let i = 0; i < bound_importance_scores.length; i++) {
      let bound_importance_val = bound_importance_scores[i];
      let topicId = i.toString(10);
      let slider = document.getElementById(`topic_${topicId}_slider`);

      slider.value = `${bound_importance_val}`
      apply.push(slider.value)
      // reset.push(slider.value);

      slider.oninput = function() {
        let html_str = ` ${this.value} `;
        
        // updated the sliders value, so use the value from the sliders
        if (modifiedTopicConstraints[i] == false) {
          modifiedTopicConstraints[i] = true;
        }
      }
      topicSliderColor(i)
    }
    // buttonStorage["undo"].push(apply.join(','));
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

  function compile_bounds_stats() {
    center_offsets = []
    center_slopes = []
    bound_offsets = []
    bound_slopes = []
    r_maxs = []

    for (let i = 0; i < bounds.length; i++) {
      let r_max = bounds[i][1] - bounds[i][0];
      r_maxs.push(r_max);
      center_offsets.push((r_max / 2.0) + bounds[i][0]);
      center_slopes.push((r_max - (r_min/2.0))/196.0); 

      bound_offsets.push(r_max / 2.0);
      bound_slopes.push(((r_max / 2.0) - (r_min/2.0))/98.0);
    }
  }

  // implements importance scores -> bound component of proposed slider algorithm v2
  //When changeing the value of the slider for each topic
  function get_bounds_from_importance_scores(bound_idx, slider_val) {

    let center = center_slopes[bound_idx]*slider_val + center_offsets[bound_idx];

    
    let bound_offset = bound_offsets[bound_idx] - Math.abs(bound_slopes[bound_idx]*slider_val);


    let lower_bound = (center - bound_offset)
    let upper_bound = (center + bound_offset)

    if (lower_bound < 0){
      lower_bound = 0.0;
    }

    return [lower_bound, upper_bound];
  }

  // implements bounds -> importance score component of proposed slider algorithm v2
  function get_bounds_importance_scores() {
    let importance_scores = []

    for (let i = 0; i < bounds.length; i++) {
      importance_scores.push(0);
    }
    prev_slider_values = importance_scores;
    return importance_scores;
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
