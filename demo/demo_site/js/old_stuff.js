// old version of show PaQL
        // insert = function insert(main_string, ins_string, pos) {
        //   return (
        //     main_string.slice(0, pos) + ins_string + main_string.slice(pos)
        //   );
        // };

        // let idx_from = first_frag_str.indexOf("FROM");
        // first_frag_str = insert(first_frag_str, "", idx_from);
        // let idx_where = first_frag_str.indexOf("WHERE");
        // first_frag_str = insert(first_frag_str, "", idx_where);
        // let idx_such_that = first_frag_str.indexOf("SUCH THAT");
        // first_frag_str = insert(first_frag_str, "", idx_such_that);

        // document.getElementById("text-PaQL").innerHTML =
        //   '<span style="cursor:default;">' + first_frag_str + "</span>";
        // nTopics = topic_lines.length;
        // for (let i = 0; i < topic_lines.length; i++) {
        //   let span = document.createElement("DIV");
        //   let topicId = topic_lines[i].topic_id.toString(10);
        //   span.setAttribute("id", "topic" + topicId);
        //   span.setAttribute("class", "paql-constraint");
        //   let formattedQueryText = `SUM(<span id=${topicId} class="paql_topic_number" style="color:blue;">topic_${
        //     topicId - 1
        //   }</span>)  
        //                                         BETWEEN  <div contenteditable id="lower_bound_${i}" class="bound">${
        //     topic_lines[i].lb
        //   }</div>  
        //                                         AND  <div contenteditable class="bound" id="upper_bound_${i}">${
        //     topic_lines[i].ub
        //   }</div>  AND <br>`;

        //   span.innerHTML = formattedQueryText;
        //   document.getElementById("text-PaQL").appendChild(span);

        //   document.getElementById(topicId).onclick = function () {
        //     console.log(this.value);

        //     if (selectedPaqlLine.style.visibility == "hidden") {
        //       selectedPaqlLine.style.visibility = "visible";
        //     } else {
        //       if (
        //         document.getElementById("selectedPaqlLine").innerHTML ==
        //         topic_lines[i].details
        //       ) {
        //         selectedPaqlLine.style.visibility = "hidden";
        //       }
        //     }

        //     document.getElementById("selectedPaqlLine").innerHTML =
        //       topic_lines[i].details;
        //   };
        // }

        // $(".bound").keypress(function (event) {
        //   allow = [43, 46, 45, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57];

        //   if (!allow.includes(event.keyCode)) {
        //     event.preventDefault();
        //   }
        //   let len = $(this).text().length;
        //   if (len > 6) {
        //     event.preventDefault();
        //   }
        // });

        // let last_frag = document.createElement("div");
        // last_frag.setAttribute("id", "last_frag");
        // last_frag.innerHTML = data.last_segment;
        // document.getElementById("text-PaQL").appendChild(last_frag);