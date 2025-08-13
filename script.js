// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk';

// Initialize Supabase client
const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function submitPost() {
  const subreddit = "r/" + (document.getElementById("subredditInput").value || "society_sim");
  const title = document.getElementById("title").value;
  const content = document.getElementById("content").value;
  const submissionFlair = document.getElementById("submissionFlair").value;
  const usernameFlair = document.getElementById("usernameFlair").value;
  const isNSFW = document.getElementById("isNSFW").checked;

  document.getElementById("subredditDisplay").innerText = subreddit;

  const simulatedScore = Math.floor(Math.random() * 200) - 100;
  const comments = [
    "Wow, really interesting take!",
    "I'm not sure I agree with this, but it's a good post.",
    "This is exactly what I needed to read today."
  ];

  document.getElementById("simulationResult").innerHTML = `
    <div class="post-preview">
      <h3>${title}</h3>
      <p><em>Posted by u/username ${usernameFlair ? `| ${usernameFlair}` : ""} | ${submissionFlair ? `| ${submissionFlair}` : ""}</em> ${isNSFW ? "| 🔞 NSFW" : ""}</p>
      <p>LLM 模擬分數：👍 ${Math.max(0, simulatedScore)} 👎 ${Math.max(0, -simulatedScore)}</p>
      <hr/>
      <h4>討論串</h4>
      <ul>
        ${comments.slice(0, 3).map(c => `<li>${c}</li>`).join("")}
      </ul>
    </div>
  `;

  const { data, error } = await supabaseClient
    .from('test_table')
    .insert([{
      subreddit,
      title,
      content,
      submissionFlair,
      usernameFlair,
      isNSFW,
      simulatedScore,
      created_at: new Date().toISOString()
    }]);

  if (error) {
    console.error("上傳到 Supabase 失敗：", error.message);
  } else {
    console.log("貼文已成功儲存到 Supabase", data);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const loadDataBtn = document.getElementById('loadDataBtn');
  const output = document.getElementById('output');
  const subredditInput = document.getElementById("subredditInput");
  const titleInput = document.getElementById("title");
  const contentInput = document.getElementById("content");
  const submitBtn = document.getElementById("submitBtn");
  const titleCounter = document.getElementById("title-counter");
  const contentCounter = document.getElementById("content-counter");
  const darkModeToggle = document.getElementById('darkModeToggle');

  // Function to update character counters
  function updateCounter(inputElement, counterElement, maxLength) {
    const currentLength = inputElement.value.length;
    counterElement.textContent = `${currentLength}/${maxLength}`;
  }

  async function loadData() {
    output.textContent = 'Loading...';
    const { data, error } = await supabaseClient.from('test_table').select('*');
    if (error) {
      output.textContent = 'Error: ' + error.message;
    } else {
      output.textContent = JSON.stringify(data, null, 2);
    }
  }

  // Enable/disable submit button based on required fields
  function validateForm() {
    const allFilled = subredditInput.value.trim() !== '' &&
                      titleInput.value.trim() !== '' &&
                      contentInput.value.trim() !== '';
    submitBtn.disabled = !allFilled;
  }

  // Event listeners
  loadDataBtn.addEventListener('click', loadData);
  submitBtn.addEventListener('click', submitPost);

  subredditInput.addEventListener("input", (e) => {
    document.getElementById("subredditDisplay").innerText = "r/" + (e.target.value || "society_sim");
    validateForm();
  });

  titleInput.addEventListener('input', () => {
    updateCounter(titleInput, titleCounter, 100);
    validateForm();
  });

  contentInput.addEventListener('input', () => {
    updateCounter(contentInput, contentCounter, 10000);
    validateForm();
  });

  // Initialize counters and form state
  updateCounter(titleInput, titleCounter, 100);
  updateCounter(contentInput, contentCounter, 10000);
  validateForm();

  // Dark mode toggle functionality
  darkModeToggle.addEventListener('change', () => {
    document.body.classList.toggle('dark-mode', darkModeToggle.checked);
  });
});