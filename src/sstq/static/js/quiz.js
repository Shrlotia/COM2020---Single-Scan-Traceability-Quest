let selectedCategory = null;
let selectedAnswers = [];

async function renderGame(tier, category) {
    try{
        const res = await fetch("/quiz_game", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tier: tier, category: category })
        });

        if (!res.ok) {
            const text = await res.text();
            console.error("Server error:", text);
            return;
        };

        const questions = await res.json();
        const main_section= document.getElementById("button-leaderboard-grid");
        const questions_div= document.getElementById("questions");

        main_section.style.display = "none";   // alternative to .hidden
        questions_div.style.display = "block";  // alternative to .hidden

        let question_count= 0;
        
        console.log(questions);
        show(question_count, questions);
    }catch (err) {
        console.error("Error loading questions:", err);
    }
}

function show(count, questions){
    let question = document.getElementById("questions");
    let [first, second, third, fourth] = questions[count].choices;

    question.innerHTML = `
    <h2>Question ${count+1}/${questions.length}</h2>
    <div id="progress_bar" class="progress_bar">
        <div class="progress_bar_full" id="progress_bar_full"></div>
    </div>
    <h3>${questions[count].question}</h3>
    <ul class="option_group">
        <li class="option">${first}</li> 
        <li class="option">${second}</li> 
        <li class="option">${third}</li>
        <li class="option">${fourth}</li>
    </ul>
    <button class="next-button" id="next-button">Next Question</button>
    `;

    const progressBarFull = document.getElementById("progress_bar_full");
    progressBarFull.style.width = `${((count+1)/questions.length)*100}%`;
    
    toggleActive();

    document.getElementById("next-button").onclick = () => {
        const selectedAnswer = document.querySelector(".option.active");

        if (!selectedAnswer){
            alert("Please select an answer to continue");
            return;
        }

        selectedAnswers.push(selectedAnswer.textContent.trim());

        count++;
        if (count < questions.length) {
            show(count, questions);
        } else {
            sendAnswers(selectedAnswers);
        }
    };
}

function toggleActive(){
    const options = document.querySelectorAll("li.option");
    options.forEach(opt => {
        opt.onclick = () => {
            options.forEach(o => o.classList.remove("active"));
            opt.classList.add("active");
        };
    });
}

document.getElementById("category-submit").addEventListener("click", () => {
    selectedCategory = document.getElementById("category").value;
    document.getElementById("button-grid").style.display = "flex";
});

document.querySelector(".basic-button").addEventListener("click", () => {
    renderGame("Basic", selectedCategory);
});

document.querySelector(".intermediate-button").addEventListener("click", () => {
    renderGame("Intermediate", selectedCategory);
});

document.querySelector(".advanced-button").addEventListener("click", () => {
    renderGame("Advanced", selectedCategory);
});