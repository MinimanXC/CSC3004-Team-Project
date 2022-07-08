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

// on-click of "Invalidate Blockchain" button, show a confirmation popup
const invalid_btn = document.querySelector("#invalidate-btn");
invalid_btn.addEventListener("click", function () {
  let confirmAction = confirm("Confirm invalidating Blockchain?");
  if (confirmAction) {
    invalidateBC(); // Executed only when user confirmed true
  }

});

// This function will submit a POST request to the backend codes and execute the function invalidate_blockchain()
function invalidateBC() {
  // Which function to be executed is through the fetch and path to the function
  fetch('http://127.0.0.1:4444/invalidatebc',{
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
    // Extract the data sent back from invalidate_blockchain() and display it out to the user
    if (res.data[0] == false) {
      invalid_block_id = res.data[1]

      // Change valid icon to invalid
      document.getElementById("validity-img").src = "/static/invalid.png";
      
      // Display comment to below invalid.png on which block was tampered
      comment = "Block " + invalid_block_id + " has been tampered with!"
      document.getElementById("invalidate-comment").innerHTML = comment;

      // Disable invalidate blockchain button since its already invalidated
      document.getElementById("invalidate-btn").disabled = true;

      // Add red highlight around invalid block and scroll to its view
      document.getElementById("block-"+invalid_block_id).classList.add("active-invalid");
      document.getElementById("block-"+invalid_block_id).scrollIntoView({ block: 'end',  behavior: 'smooth' });

      // Replace hash and modified data of invalid block
      document.getElementById("block-" + invalid_block_id + "-hash").innerHTML = res.data[2];
      document.getElementById("block-" + invalid_block_id + "-data").innerHTML = res.data[3];

    }
    
  }).catch(error => console.error('Error:', error));

}