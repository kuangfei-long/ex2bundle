let url_prefix = "http://127.0.0.1:5000/";
$(document).ready(function () {
  let nTopics = 10;
  let bounds = "";
  let data_states = [];
  let data_sentences = [];
  let sentenceArray = [];
  let submittedSummary = [];
  let keywordInfo;
  let currentLabel = "";
  let submitButton = document.getElementById("submitSummary");
  let updateButton = document.getElementById("updateSummary");
  let learnSummaryButton = document.getElementById("button_learnSummary");
  let generateSummaryButton = document.getElementById("button_generateSummary");
  let dropdown_input = document.getElementById("inputDocumentSelector");
  let dropdown_output = document.getElementById("outputDocumentSelector");
  let dropdown_topic = document.getElementById("topicDocumentSelector");
  let explanationWindow = document.getElementById("explanation_view");
  let barchartButton = document.getElementById("barchartButton");
  let wordCloudButton = document.getElementById("wordCloudButton");


  // let slider_interval_min = 0.5;
  // let slider_interval_max = 1.5;
  // let step_size = 0.0;
  // let num_intervals = 0;
  // let num_steps = 0;
  var userID;
  var recordInteractions = true;
  let showExplanation = false;
  let modifiedTopicConstraints = [];
  let currOpenTopic = -1;
  let displayBarChart = 1;
  

  if (window.localStorage.getItem("userID_sus") === null) {
    userID = makeRandomId();
    window.localStorage.setItem("userID_sus", userID);
  } else {
    userID = window.localStorage.getItem("userID_sus");
  }
  console.log("user ID", userID);

  submitButton.setAttribute("disabled", "disabled");
  updateButton.setAttribute("disabled", "disabled");
  learnSummaryButton.setAttribute("disabled", "disabled");
  generateSummaryButton.setAttribute("disabled", "disabled");
  dropdown_output.setAttribute("disabled", "disabled");
  explanationWindow.style.display = "none";
  barchartButton.style.visibility = "hidden";
  wordCloudButton.style.visibility = "hidden";

  $("#barchartButton").click(function() {
    displayBarChart = 1;

    if (currOpenTopic != -1) {
      displayFocusedTopicView(currOpenTopic);
    }
  });

  $("#wordCloudButton").click(function() {
    displayBarChart = 0;

    if (currOpenTopic != -1) {
      displayFocusedTopicView(currOpenTopic);
    }
  });


  // first scroll to top, then disable
  // document.body.style.overflow = 'visible';
  // window.scrollTo({top : 0,  behavior: 'auto'});

  // setTimeout(function () {
  //   document.body.style.overflow = 'hidden';
  // }, 500)
  

  $.ajax({
    url: url_prefix + "get_states",
    async: true,
    type: "GET",
    dataType: "json",
    success: function (data) {
      data_states = data;
      
      let option_topic = document.createElement("OPTION");
      option_topic.innerHTML = "All Documents";
      option_topic.value = "topics-1";
      dropdown_topic.options.add(option_topic);
      
      for (let i = 0; i < data_states.length; i++) {
        let option_input = document.createElement("OPTION");
        option_input.innerHTML = data_states[i].state_name;
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
        dropdown_topic.options.add(option_topic);
      }
    },
  });

  // populate the accordian headers with the approperiate topics
  populateTopicKeywords(-1);

  // doing it one at a time now for test purposes
  $("#genSumInfoIcon").popover("enable");
  $("#sumSelectorInfoIcon").popover("enable");
  $("#exSumInfoIcon").popover("enable");
  $("#PaQLInfoIcon").popover("enable");
  $("#submitSummary").popover({ trigger: "manual", placement: "top" });
  $("#updateSummary").popover({ trigger: "manual", placement: "top" });
  $("#button_learnSummary").popover({ trigger: "manual", placement: "top" });
  $("#button_generateSummary").popover({ trigger: "manual", placement: "top" });


  $(document).on('shown.bs.collapse', '#topicKeywordAccordion', function(e) {
    let selected_topic_id = parseInt($(e.target).attr('aria-labelledby').substring(18), 10);
    currOpenTopic = selected_topic_id;
    barchartButton.style.visibility = "visible";
    wordCloudButton.style.visibility = "visible";
    hide_all_names_sliders_but(selected_topic_id);
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  });


  $(document).on('show.bs.collapse', '#topicKeywordAccordion', function(e) {
    let selected_topic_id = parseInt($(e.target).attr('aria-labelledby').substring(18), 10);
    currOpenTopic = selected_topic_id;
    barchartButton.style.visibility = "visible";
    wordCloudButton.style.visibility = "visible";
    displayFocusedTopicView(selected_topic_id);
  });

  $(document).on('hidden.bs.collapse', '#topicKeywordAccordion', function(e) {
    let selected_topic_id = parseInt($(e.target).attr('aria-labelledby').substring(18), 10);
    barchartButton.style.visibility = "hidden";
    wordCloudButton.style.visibility = "hidden";
    currOpenTopic = -1;
    displayBarChart = 1; // always display barchart first by default
    show_topic_names_sliders();
  });


  $(".document").hide();
  let prevLabel = "";
  $("#inputDocumentSelector").change(function () {
    currentLabel = $(this).val();
    let idx = parseInt(currentLabel.substring(3));

    let docId = idx.toString(10);
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
        let currStateId = data_states[idx].state_id;

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
          document.getElementById("doc" + currStateId).appendChild(span);
          let space_span = document.createElement("SPAN");
          space_span.textContent = " ";
          document.getElementById("doc" + currStateId).appendChild(space_span);
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

    let docName = data_states[idx].state_name;
    if (document.getElementById(docName) === null) {
      submitButton.removeAttribute("disabled");
      updateButton.setAttribute("disabled", "disabled");
    } else {
      updateButton.removeAttribute("disabled");
      submitButton.setAttribute("disabled", "disabled");
    }

    if (document.getElementById(prevLabel) !== null) {
      document.getElementById(prevLabel).remove();
    }
    prevLabel = currentLabel;
  });


  $("#topicDocumentSelector").change(function () {
    currentLabel = $(this).val();
    let idx = parseInt(currentLabel.substring(6));
    let docId = idx.toString(10);

    populateTopicKeywords(idx);

  });

  let selectedState = "None";
  $(".generatedDoc").hide();


  $("#button_generateSummary").click(function() {
    $(".generatedDoc").hide();
    // get the value of the currently selected item
    var select = document.getElementById('outputDocumentSelector');
    let currentLearnedLabel = select.options[select.selectedIndex].value;

    // get the name of the selected state from the dropdown
    selectedState = $("#outputDocumentSelector option:selected").text();

    if (currentLearnedLabel == 0) {
      $("#submitSummary").popover("hide");
      alert("Please select a state to summarize.");
      return;
    } else {
      $("#button_generateSummary").popover("toggle");
      setTimeout(function () {
        $("#button_generateSummary").popover("hide");
      }, 2000);
    }

    if (showExplanation == false) {
      explanationWindow.style.display = "block"
      explanationWindow.style.visibility = "visible";
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
      showExplanation = true;
    } 
    

    $("#" + currentLearnedLabel).show();
    let idx = parseInt(currentLearnedLabel.substring(14));
    let docId = idx.toString(10);
    let learnedContent = document.createElement("div");
    learnedContent.setAttribute("id", "learnedSummary" + docId);
    learnedContent.setAttribute("class", "generatedDoc");
    document.getElementById("generated").innerHTML = "";
    document.getElementById("generated").appendChild(learnedContent);

    submittedSummary_server = makeExampleSummaries();

    // add in the bounds
    // modified values use the slider results, otherwise use the learned bounds
    let summary_bounds = []

    for (let i = 0; i < bounds.length; i++) {
      if (modifiedTopicConstraints[i] == true) {
        let slider_val = document.getElementById("topic_" + (i).toString(10) + "_slider").value;
        // // math to convert slider value to bounds
        // //actually calculate new bounds
        // let upper_bound_mult = 0;
        // let lower_bound_mult = 0;
        // let gamma = Math.floor((slider_val-1)/num_steps) % 2.0;

        // // calculate the new upper bound multiplier
        // if (gamma == 0) {
        //   upper_bound_mult = Math.floor((slider_val-1)/(2*num_steps))*num_steps + (slider_val % (2*num_steps));
        // } else {
        //   upper_bound_mult = Math.ceil(slider_val/(2*num_steps))*num_steps;
        // }

        // // calculate the new lower_bound
        // lower_bound_mult = slider_val - upper_bound_mult;

        // let new_upper_bound = 0.5 + upper_bound_mult*step_size;
        // let new_lower_bound = 0.0 + lower_bound_mult*step_size;

        // // add the newwly calculated bounds to the array
        summary_bounds.push(get_bounds_from_importance_scores(i, slider_val));
      } else {
        summary_bounds.push(bounds[i]);
      }
    }

    console.log(summary_bounds)

    $.ajax({
      url: url_prefix + "get_summary",
      async: true,
      type: "POST",
      data: {
        user_id: userID,
        bounds: JSON.stringify(summary_bounds),
        state_name: selectedState,
        state_id: docId,
        example: JSON.stringify(submittedSummary_server),
      },
      beforeSend: function () {
        $("#loader").show();
        $("#loader_background").show();
      },
      success: function (data) {
        $("#loader").hide();
        $("#loader_background").hide();

        console.log(data);

        let summary = data.summary;
        let default_summ = data.default;

        document.getElementById("learnedSummary" + idx.toString(10)).innerHTML =
          summary;

        if (default_summ == true) {
          alert(
            "Topic Score Constraints too strict! No solution could be found and a default summary was returned."
          );
        }
      },
    });
  });

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

  function highlightSentence() {
    currentId = this.id;
    let curr = document.getElementById(currentId);
    selectedText = document.getElementById(currentId).textContent;
    currObj = sentenceArray.find((o) => o.document_id === currentLabel);
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
  }

  $("#searchInput").keyup(function () {
    let inputText = document.getElementById("searchInput").value.trim();
    let currDocDiv = document.getElementById(currentLabel);

    filter = inputText.toUpperCase();
    let spanArray = currDocDiv.getElementsByTagName("span");
    
    // highlight searched term in spans
    var instance = new Mark([...spanArray]);
    instance.unmark();
    instance.mark(inputText);
    
    // this work displays the relevent sentences in the doc page
    for (i = 0; i < spanArray.length; i++) {
      if (spanArray[i].textContent == " " || spanArray[i].textContent.toUpperCase().indexOf(filter) > -1) {
        spanArray[i].style.display = "";
      } else {
        spanArray[i].style.display = "none";
      }
    }
  });

  $("#submitSummary").click(function () {
    let currObj = sentenceArray.find((o) => o.document_id === currentLabel);
    if (currObj === undefined || currObj.selected.length === 0) {
      $("#submitSummary").popover("hide");
      alert("Please select at least one sentence.");
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
    let docName = data_states[idx].state_name;
    submitButton.setAttribute("disabled", "disabled");
    updateButton.removeAttribute("disabled");

    let textBox = document.createElement("div");
    textBox.setAttribute("id", docName);

    let closeBtn = document.createElement("div");
    closeBtn.setAttribute("class", "close-button");
    closeBtn.setAttribute("id", "close-" + currentLabel);
    closeBtn.setAttribute("title", "Remove this summary");
    closeBtn.onclick = removeSubmission;
    closeBtn.innerHTML = "&#x2715";

    let summaryHeader = document.createElement("div");
    summaryHeader.setAttribute("class", "summaryHeader");
    $(summaryHeader).append(
      "<div style='display: block; float: left'>" + docName + "</div>"
    );
    summaryHeader.appendChild(closeBtn);
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

    if (Object.keys(submittedSummary).length >= 2) {
      learnSummaryButton.removeAttribute("disabled");
    }
  });

  $("#updateSummary").click(function () {
    let currObj = sentenceArray.find((o) => o.document_id === currentLabel);
    let idx = parseInt(currentLabel.substring(3));
    let docName = data_states[idx].state_name;
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

    if (currObj.submitted.length === 0) {
      $("#updateSummary").popover("hide");
      alert("Please select at least one sentence");
      return;
    } else {
      $("#updateSummary").popover("toggle");
      setTimeout(function () {
        $("#updateSummary").popover("hide");
      }, 2000);
    }

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
      content = content.concat(
        " " + document.getElementById(currObj.submitted[i]).innerHTML
      );
    }
    currTextBox.textContent = content;
  });

  function removeSubmission() {
    let idx = parseInt(this.id.substring(9));
    let targetDoc = this.id.substring(6);
    let docName = data_states[idx].state_name;
    document.getElementById(docName).remove();

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
      updateButton.setAttribute("disabled", "disabled");
    }

    if (Object.keys(submittedSummary).length < 2) {
      learnSummaryButton.setAttribute("disabled", "disabled");
      dropdown_output.setAttribute("disabled", "disabled");
    }
  }

  $("#button_learnSummary").click(function () {
    if (Object.keys(submittedSummary).length < 2) {
      alert("Please give at least two example summaries!");
      $("#button_learnSummary").popover("hide");
      return;
    } else {
      $("#button_learnSummary").popover("toggle");
      setTimeout(function () {
        $("#button_learnSummary").popover("hide");
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

    bounds = "";
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
        dropdown_output.removeAttribute("disabled");
        generateSummaryButton.removeAttribute("disabled");

        for (let i = 0; i < bounds.length; i++) {
          // push variables to track changes
          modifiedTopicConstraints.push(false);

        //   // add event listeners for accordian buttons
        //   let accordian_button = document.getElementById(`accordion-button-${i}`);
        //   accordian_button.addEventListener('show.bs.collapse', function () {
        //     hide_all_names_sliders_but(i);
        //   }); 

        //   accordian_button.addEventListener('hide.bs.collapse', function() {
        //     show_topic_names_sliders();
        //   });
        }

        // calculate the resulting topic score slider values
        loadTopicSliders();
        populateTopicKeywords(-1)
      },
    });
  });

  $("#tutorial").click(function () {
    document.getElementById("tutorialVideo").pause();
  });
  $("#tutorialVideo").on("click", function (e) {
    e.preventDefault();
  });

  $("#watchTutorial").click(function () {
    document.getElementById("tutorialVideo").play();
  });


  function populateTopicKeywords(idx) {
    $.ajax({
      url: url_prefix + "get_topic_keywords?state_id=" + idx,
      async: true,
      type: "GET",
      dataType: "json",
      success: function (data) {
        let topic_lines = data.topics

        keywordInfo = data.topics

        for (let i = 0; i < topic_lines.length; i++) {
          let topic_id = topic_lines[i].topic_id
          let accordion_button = document.getElementById(`accordion-button-${topic_id}`)
          accordion_button.innerHTML = ""
          accordion_button.innerHTML = topic_lines[i].keywords
        }

        // updaet any open barcharts
        if (currOpenTopic != -1) {
          displayFocusedTopicView(currOpenTopic);
        }
      },
    });
  }

  function loadTopicSliders() {
    let bound_importance_scores = get_bounds_importance_scores();

    // console.log(bound_importance_scores)

    for (let i = 0; i < bound_importance_scores.length; i++) {
      let bound_importance_val = bound_importance_scores[i];
      let topicId = i.toString(10);
      let slider = document.getElementById(`topic_${topicId}_slider`);
      let output = document.getElementById(`topic_${topicId}_slide_dis`);

      slider.value =  `${bound_importance_val}`
      output.innerHTML = ` ${bound_importance_val} `;

      slider.oninput = function() {
        let html_str = ` ${this.value} `;
        output.innerHTML = html_str;
        
        // updated the sliders value, so use the value from the sliders
        if (modifiedTopicConstraints[i] == false) {
          modifiedTopicConstraints[i] = true;
        }
      }
    }
  }

  function makeExampleSummaries() {
    // extract the example summaires
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

  function makeRandomId() {
    var text = "";
    var possible =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 8; i++)
      text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
  }

  function logInteraction(type, content) {
    if (recordInteractions == true) {
      var dt = new Date();
      var utcDate = dt.toUTCString();
      str = userID + "," + utcDate + "," + type + "," + content + "\n";

      $.ajax({
        url: url_prefix + "log_interaction",
        async: true,
        type: "POST",
        data: {
          user_id: userID,
          content: str,
        }
      });
    }
  }

  // function get_bounds_importance_scores() {
  //   let importance_scores = []

  //   for (let i = 0; i < bounds.length; i++) {
  //     let importance_score = Math.ceil((bounds[i][1] - slider_interval_min)*2*num_steps)-1;
  //     if (importance_score < 0) {
  //       importance_score = 0;
  //     }
  //     importance_scores.push(importance_score);
  //   }
  //   return importance_scores;

  // }

  function get_bounds_from_importance_scores(bound_idx, slider_val) {
    let bound_ranges = [];
    let max_bound = -1.0;

    for (let i = 0; i < bounds.length; i++) {
      let bound_range = bounds[i][1] - bounds[i][0];
      bound_ranges.push(bound_range)
      if (bounds[i][1] > max_bound) {
        max_bound = bounds[i][1];
      }
    }

    let max_range = Math.max.apply(Math, bound_ranges)/2.0;
    let min_range = Math.min.apply(Math, bound_ranges)/2.0;

    let center = ((max_bound - 0.05)/200.0)*slider_val + (max_bound/2.0);
    let bound_offset = max_range - Math.abs(((max_range - min_range)/100)*slider_val);

    // console.log(center)
    // console.log(bound_offset)

    let lower_bound = (center - bound_offset);
    let upper_bound = (center + bound_offset)

    if (lower_bound < 0){
      lower_bound = 0.0;
    }

    if (upper_bound > max_bound) {
      upper_bound = max_bound;
    }

    return [lower_bound, upper_bound];
  }

  function get_bounds_importance_scores() {
    let importance_scores = []
    let max_bound = -1.0; 

    for (let i = 0; i < bounds.length; i++) {
      if (bounds[i][1] > max_bound) {
        max_bound = bounds[i][1];
      }
    }

    for (let i = 0; i < bounds.length; i++) {
      let importance_score = Math.round((bounds[i][1] - (max_bound/2.0))/((max_bound - 0.05) / 200.0));
      // console.log(importance_score)
      if (importance_score < -100) {
        importance_score = -100;
      } else if (importance_score > 100) {
        importance_score = 100;
      }
      importance_scores.push(importance_score);
    }
    return importance_scores;
  }


  function show_topic_names_sliders() {
    for (let i = 0; i < bounds.length; i++) {
      let topic_slider_name = `topic${i}_slider_entry`;
      let topic_name_name = `topic${i}_name`;
      let accord_button = `accordion-button-${i}`;

      let topic_slider = document.getElementById(topic_slider_name);
      let topic_name = document.getElementById(topic_name_name);
      let topic_accord_button = document.getElementById(accord_button);

      topic_slider.style.display = "block";
      topic_name.style.display = "block";
      topic_accord_button.style.opacity = 1.0;
    }
  }

  function hide_all_names_sliders_but(topic_idx) {    
    for (let i = 0; i < bounds.length; i++) {
      if (i != topic_idx) {
        let topic_slider_name = `topic${i}_slider_entry`;
        let topic_name_name = `topic${i}_name`;
        let accord_button = `accordion-button-${i}`;

        let topic_slider = document.getElementById(topic_slider_name);
        let topic_name = document.getElementById(topic_name_name);
        let topic_accord_button = document.getElementById(accord_button);


        topic_slider.style.display = "none";
        topic_name.style.display = "none";
        topic_accord_button.style.opacity = 0.25;
      }
    }
  }

  function build_barchart(topic_idx) {

    if (keywordInfo == null) {
      alert("No keyword information available! Please click Learn Summarization Button!");
      return;
    }

    let accord_body_str = `accordion-body-${topic_idx}`;
    let cur_body = document.getElementById(accord_body_str);
    let div_width = cur_body.clientWidth;

    div_width = 900;

    // console.log(div_width);

    let state_keyword_info = keywordInfo[topic_idx];

    // get the name of the selected state from the dropdown
    selectedState = $("#topicDocumentSelector option:selected").text();

    var data = []

    for (let i = 0; i < state_keyword_info["topic_words"].length; i++) {
      data.push({"name" : state_keyword_info["topic_words"][i],
                 "value" : state_keyword_info["counts"][i]})
    }

    //sort bars based on value
    data = data.sort(function (a, b) {
      return d3.ascending(a.value, b.value);
    })

    //set up svg using margin conventions - we'll need plenty of room on the left for labels
    var margin = {
      top: 15,
      right: 30,
      bottom: 15,
      left: 80
    };

    var width = div_width - margin.left - margin.right;
    var height = 350 - margin.top - margin.bottom;


    let selected_graphic = `#topic_${topic_idx}_graphic`;

    document.getElementById(`topic_${topic_idx}_graphic`).innerHTML = "";

    var svg = d3.select(selected_graphic).append("svg:svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    
    var x = d3.scaleLinear()
      .range([0, width])
      .domain([0, d3.max(data, function (d) {
      return d.value;
    })]);

    var y = d3.scaleBand()
    .rangeRound([height, 0])
    .domain(data.map(function (d) {
        return d.name;
      })) 
    .padding(0.1);

    //make y axis to show bar names
    var yAxis = d3.axisLeft(y)
    //no tick marks
    .tickSize(0)

    var gy = svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)

    var bars = svg.selectAll(".bar")
      .data(data)
      .enter()
      .append("g")

    //append rects
    bars.append("rect")
        .attr("class", "bar")
        .attr("y", function (d) {
            return y(d.name);
        })
        .attr("height", y.bandwidth())
        .attr("x", 0)
        .attr("width", function (d) {
            return x(d.value);
        })
        .attr("style", "fill:forestgreen")

    //add a value label to the right of each bar
    bars.append("text")
      .attr("class", "label")
      //y position of the label is halfway down the bar
      .attr("y", function (d) {
          return y(d.name) + y.bandwidth() / 2 + 4;
      })
      //x position is 3 pixels to the right of the bar
      .attr("x", function (d) {
          return x(d.value) + 3;
      })
      // .attr("color", )
      .text(function (d) {
          return d.value;
      });
  }

  function buildWordCloud(topic_idx) {
    if (keywordInfo == null) {
      alert("No keyword information available! Please click Learn Summarization Button!");
      return;
    }

    let accord_body_str = `accordion-body-${topic_idx}`;
    let cur_body = document.getElementById(accord_body_str);
    let div_width = cur_body.clientWidth;

    div_width = 900;

    let state_keyword_info = keywordInfo[topic_idx];

    // get the name of the selected state from the dropdown
    selectedState = $("#topicDocumentSelector option:selected").text();

    var data = [];
    let maxCtr = 0;
    let minCtr = 1;

    for (let i = 0; i < state_keyword_info["topic_words"].length; i++) {
      // console.log(state_keyword_info["counts"][i])
      data.push({"word" : state_keyword_info["topic_words"][i],
                 "size" : state_keyword_info["counts"][i]});

      if (state_keyword_info["counts"][i] > maxCtr) {
        maxCtr = state_keyword_info["counts"][i];
      }

      if (state_keyword_info["counts"][i] < minCtr) {
        minCtr = state_keyword_info["counts"][i];
      }
    }

    // scale the size for display
    for (let i = 0; i < data.length; i++) {
      let temp_dict = data[i];
      temp_dict.size = scaleNumber(temp_dict.size, minCtr, maxCtr, 10, 50);
    }

    //set up svg using margin conventions - we'll need plenty of room on the left for labels
    var margin = {
      top: 5,
      right: 5,
      bottom: 5,
      left: 5
    };

    var width = div_width - margin.left - margin.right;
    var height = 350 - margin.top - margin.bottom;

    let selected_graphic = `#topic_${topic_idx}_graphic`;

    document.getElementById(`topic_${topic_idx}_graphic`).innerHTML = "";

    var svg = d3.select(selected_graphic).append("svg:svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // Constructs a new cloud layout instance. It run an algorithm to find the position of words that suits your requirements
    // Wordcloud features that are different from one word to the other must be here
    var layout = d3.layout.cloud()
      .size([width, height])
      .words(data.map(function(d) { return {text:d.word, size:d.size}; }))
      .padding(5)        //space between words
      .rotate(function() { return (~~(Math.random() * 6) - 3) * 30; })
      .fontSize(function(d) { return d.size;})      // font size of words
      .on("end", draw);
    layout.start();

    function draw(words) {
      svg.append("g")
      .attr("transform", "translate(" + layout.size()[0] / 2 + "," + layout.size()[1] / 2 + ")")
      .selectAll("text")
        .data(words)
      .enter().append("text")
        .style("font-size", function(d) { return d.size + "px"; })
        .style("fill", "forestgreen")
        .attr("text-anchor", "middle")
        .style("font-family", "Impact")
        .attr("transform", function(d) {
          return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
        })
        .text(function(d) { return d.text; });
    }
  }


  function scaleNumber(number, minIn, maxIn, minOut, maxOut) {
    return Math.round((number - minIn) * ((maxOut - minOut) / (maxIn - minIn)) + minOut);
  }

  function displayFocusedTopicView(topic_idx) {
    if (displayBarChart == 0) {
      buildWordCloud(topic_idx);
    } else {
      build_barchart(topic_idx);
    }
  }

});
