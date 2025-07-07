document.addEventListener("DOMContentLoaded", function () {
  const pdfSelect = document.getElementById("pdfSelect");
  const queryRadios = document.getElementsByName("queryType");
  const dynamicInputs = document.getElementById("dynamicInputs");

  let cachedData = {};

  function clearDynamicInputs() {
    dynamicInputs.innerHTML = "";
  }

  function disableRadios() {
    queryRadios.forEach(r => r.disabled = true);
  }

  function enableRadios() {
    queryRadios.forEach(r => r.disabled = false);
  }

  disableRadios();

  function createDropdown(id, labelText, options, placeholder) {
    const container = document.createElement("div");
    container.classList.add("form-group");

    const label = document.createElement("label");
    label.setAttribute("for", id);
    label.textContent = labelText;

    const select = document.createElement("select");
    select.id = id;
    select.name = id;
    select.classList.add("custom-select");

    const defaultOption = document.createElement("option");
    defaultOption.disabled = true;
    defaultOption.selected = true;
    defaultOption.textContent = placeholder;
    select.appendChild(defaultOption);

    options.forEach(opt => {
      const option = document.createElement("option");
      option.value = opt.page;
      option.textContent = opt.title;
      select.appendChild(option);
    });

    container.appendChild(label);
    container.appendChild(select);
    return container;
  }

  // Populate PDF dropdown
  fetch("/get_pdfs")
    .then(res => res.json())
    .then(data => {
      data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.filename;
        option.textContent = item.display;
        pdfSelect.appendChild(option);
      });
    });

  // Fetch all cached titles
  fetch("/get_cached_titles")
    .then(res => res.json())
    .then(data => {
      cachedData = data;
    })
    .catch(err => console.error("Failed to load cached titles:", err));

  pdfSelect.addEventListener("change", () => {
    const selectedPDF = pdfSelect.value;
    if (!selectedPDF || !cachedData[selectedPDF]) return;

    clearDynamicInputs();
    queryRadios.forEach(r => {
      r.disabled = false;
      r.checked = false;
    });
  });

  queryRadios.forEach(radio => {
    radio.addEventListener("change", () => {
      clearDynamicInputs();

      const pdf = pdfSelect.value;
      if (!pdf || !cachedData[pdf]) return;

      const data = cachedData[pdf];
      const selectedType = radio.value;

      if (selectedType === "part") {
        const partDropdown = createDropdown("partSelect", "Select Part:", data.parts, "Choose a Part");
        dynamicInputs.appendChild(partDropdown);

      } else if (selectedType === "section") {
        const partDropdown = createDropdown("sectionPartSelect", "Select Part:", data.parts, "Choose a Part");
        const sectionDropdown = createDropdown("sectionSelect", "Select Section:", [], "Choose a Section");

        const partSelect = partDropdown.querySelector("select");

        partSelect.addEventListener("change", function () {
          const selectedPart = this.selectedOptions[0].textContent;
          const sections = data.sections[selectedPart] || [];

          const sectionSelect = sectionDropdown.querySelector("select");
          sectionSelect.innerHTML = "";

          const defaultOption = document.createElement("option");
          defaultOption.disabled = true;
          defaultOption.selected = true;
          defaultOption.textContent = "Choose a Section";
          sectionSelect.appendChild(defaultOption);

          sections.forEach(sec => {
            const option = document.createElement("option");
            option.value = sec.page;
            option.textContent = sec.title;
            sectionSelect.appendChild(option);
          });
        });

        dynamicInputs.appendChild(partDropdown);
        dynamicInputs.appendChild(sectionDropdown);

      } else if (selectedType === "subsection") {
        const partDropdown = createDropdown("subPartSelect", "Select Part:", data.parts, "Choose a Part");
        const sectionDropdown = createDropdown("subSectionSelect", "Select Section:", [], "Choose a Section");
        const subDropdown = createDropdown("subSelect", "Select Subsection:", [], "Choose a Subsection");

        const partSelect = partDropdown.querySelector("select");
        const sectionSelect = sectionDropdown.querySelector("select");
        const subSelect = subDropdown.querySelector("select");

        partSelect.addEventListener("change", function () {
          const partTitle = this.selectedOptions[0].textContent;
          const sections = data.sections[partTitle] || [];

          sectionSelect.innerHTML = "";
          const defaultSec = document.createElement("option");
          defaultSec.disabled = true;
          defaultSec.selected = true;
          defaultSec.textContent = "Choose a Section";
          sectionSelect.appendChild(defaultSec);

          sections.forEach(sec => {
            const option = document.createElement("option");
            option.value = sec.page;
            option.textContent = sec.title;
            sectionSelect.appendChild(option);
          });

          subSelect.innerHTML = "";
          const defaultSub = document.createElement("option");
          defaultSub.disabled = true;
          defaultSub.selected = true;
          defaultSub.textContent = "Choose a Subsection";
          subSelect.appendChild(defaultSub);
        });

        sectionSelect.addEventListener("change", function () {
          const partTitle = partSelect.selectedOptions[0].textContent;
          const sectionTitle = this.selectedOptions[0].textContent;
          const allSections = data.sections[partTitle] || [];
          const selectedSec = allSections.find(sec => sec.title === sectionTitle);
          const subsections = selectedSec?.subsections || [];

          subSelect.innerHTML = "";
          const defaultSub = document.createElement("option");
          defaultSub.disabled = true;
          defaultSub.selected = true;
          defaultSub.textContent = "Choose a Subsection";
          subSelect.appendChild(defaultSub);

          subsections.forEach(sub => {
            const option = document.createElement("option");
            option.value = sub.page_number;
            option.textContent = sub.title;
            subSelect.appendChild(option);
          });
        });

        dynamicInputs.appendChild(partDropdown);
        dynamicInputs.appendChild(sectionDropdown);
        dynamicInputs.appendChild(subDropdown);
      }
    });
  });

  // Submission
  document.getElementById("bluebookForm").addEventListener("submit", function (e) {
    e.preventDefault();
    const pdf = pdfSelect.value;
    const queryType = [...queryRadios].find(r => r.checked)?.value;

    if (!pdf || !queryType) {
      alert("Please complete all fields.");
      return;
    }

    let page = null;
    if (queryType === "part") {
      page = document.getElementById("partSelect")?.value;
    } else if (queryType === "section") {
      page = document.getElementById("sectionSelect")?.value;
    } else if (queryType === "subsection") {
      page = document.getElementById("subSelect")?.value;
    }

    if (!page) {
      alert("Please make a valid selection.");
      return;
    }

    window.open(`/view_pdf/${pdf}?page=${page}`, "_blank");
  });
});




