const blocks = document.querySelectorAll(".block");
blocks.forEach(
  // Make selected block active

  (block) =>
    (block.onclick = () => {
      document.querySelectorAll(".block").forEach((block) => {
        block.classList.remove("active");
      });
      block.classList.add("active");
    })
);

const invalid_btn = document.querySelector("#invalidate-btn");
invalid_btn.addEventListener("click", function () {
  let confirmAction = confirm("Confirm invalidating Blockchain?");
  if (confirmAction) {
    invalidateBC();
  }

});

function invalidateBC() {
  fetch('http://127.0.0.1:5000/invalidatebc',{
    method: 'POST',
    headers: {
      'Content-type': 'application/json; charset=UTF-8',
      'Accept': 'application/json'
    }
  }).then(response => 
    response.json().then(data => ({
      data: data
    })
  )).then(res => {
    if (res.data == false) {
      document.getElementById("validity-img").src = "/static/invalid.png";
      document.getElementById("invalidate-btn").disabled = true;
    } else {
      document.getElementById("validity-img").src = "/static/valid.png";
    }
  }).catch(error => console.error('Error:', error));

}