function renderPlayGrid(){
    const playHTML='<button class="play_button">Play</button>';
    document.querySelector('.left_section').innerHTML = playHTML;
}

function renderDifficultyGrid(){
    const difficultyHTML = `
        <button class="difficulty_button">Easy</button>
        <button class="difficulty_button">Medium</button>
        <button class="difficulty_button">Hard</button>
        <button class="cancel_button">cancel</button>
    `;
    document.querySelector('.left_section').innerHTML = difficultyHTML;
}
renderPlayGrid();
document.addEventListener('click', (e) => {
  if (e.target.matches('.play_button')) {
    renderDifficultyGrid();
  }

  if (e.target.matches('.cancel_button')) {
    renderPlayGrid();
  }

  if (e.target.matches('.difficulty_button')) {
    console.log('Difficulty:', e.target.textContent);
  }
});