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

// For getting number of blocks and displaying to user
// setTimeout(() => {
//   const numberOfBlocks = (document.querySelector("#nrBlocks").innerText =
//     blocks.length);
// }, 1000);