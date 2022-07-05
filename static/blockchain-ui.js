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
  alert("Invalid btn");
});
