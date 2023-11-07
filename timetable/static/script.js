function genCourseURL() {
    var course = document.getElementById("course-input").value;
    if (course) {
        document.getElementById("course-url").innerHTML = `https://timetable.redbrick.dcu.ie/api?course=${course}`;
    }
}
function genModuleURL() {
    var children = document.getElementById("modules-container").children;
    if (children.length > 0) {
        let modules = [];
        for (let i = 0; i < children.length; i++) {
            modules.push(children[i].children[0].innerHTML);
        };
        document.getElementById("module-url").innerHTML = `https://timetable.redbrick.dcu.ie/api?modules=${modules.join(',')}`;
    }
}
const handleRemove = e => {
    const item = e.target.closest(".item");
    
    // Remove the listener.
    item.querySelector(".remove-btn")
        .removeEventListener("click", handleRemove);
    
    item.parentElement.removeChild(item);
};
function addModule() {
    const inputField = document.getElementById("module-input");
    if (!inputField.value) {
        return
    }
    const modulesContainer = document.getElementById("modules-container");
    
    const item = document.createElement("div");
    const paragraph = document.createElement("div");
    const remove = document.createElement("button");
    
    item.classList.add("item");
    remove.classList.add("remove-btn");
    
    paragraph.textContent = inputField.value;
    remove.textContent = "🗑️ Remove";
    
    remove.addEventListener("click", handleRemove);
    
    item.append(paragraph);
    item.append(remove);
    modulesContainer.append(item);
    
    inputField.value = "";
}
function showHide(div1, div2) {
    document.getElementById(div1).style.display = "block";
    document.getElementById(div2).style.display = "none";
    if (div1 == "courses-block") {
        document.getElementById("courses-switch").style.color = "black";
        document.getElementById("modules-switch").style.color = "grey";
    } else if (div1 == "modules-block") {
        document.getElementById("modules-switch").style.color = "black";
        document.getElementById("courses-switch").style.color = "grey";
    }
}
function copyCourse() {
    var text = document.getElementById("course-url");
    copyToClipboard(text);
}
function copyModule() {
    var text = document.getElementById("module-url");
    copyToClipboard(text);
}
function copyToClipboard(text) {
    navigator.clipboard.writeText(text.textContent);
    alert(`Copied '${text.textContent}' to clipboard.`)
}