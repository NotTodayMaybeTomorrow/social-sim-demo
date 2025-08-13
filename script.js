// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk'

// Initialize Supabase client
const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

async function submitPost() {
  const subreddit = document.getElementById("subredditInput").value || "r/society_sim"
  const title = document.getElementById("title").value
  const content = document.getElementById("content").value
  const submissionFlair = document.getElementById("submissionFlair").value
  const usernameFlair = document.getElementById("usernameFlair").value
  const isNSFW = document.getElementById("isNSFW").checked

  // 顯示 subreddit
  document.getElementById("subredditDisplay").innerText = subreddit

  // 模擬 LLM 回應
  const simulatedScore = Math.floor(Math.random() * 200) - 100
  const comments = [
    "Wow, really interesting take!",
    "Not sure I agree, but I get your point.",
    "This belongs in r/unpopularopinion.",
    "Red flag post... 🤨",
    "Can we get a source on that?",
  ]

const output = document.getElementById("output")
  output.innerHTML = `
    <div class="post-preview">
      <h3>${title}</h3>
      <p>${content}</p>
      <p><strong>${submissionFlair}</strong> | <em>${usernameFlair}</em> ${isNSFW ? "| 🔞 NSFW" : ""}</p>
      <p>LLM 模擬分數：👍 ${Math.max(0, simulatedScore)} 👎 ${Math.max(0, -simulatedScore)}</p>
      <hr/>
      <h4>討論串</h4>
      <ul>
        ${comments.slice(0, 3).map(c => `<li>${c}</li>`).join("")}
      </ul>
    </div>
  `

  // 儲存資料到 Supabase
  const { data, error } = await supabase
    .from('test_table')  // ← 請改成你的實際資料表名稱
    .insert([{
      subreddit,
      title,
      content,
      submissionFlair,
      usernameFlair,
      isNSFW,
      simulatedScore,
      created_at: new Date().toISOString()  // optional: 若有 timestamp 欄位
    }])

  if (error) {
    console.error("上傳到 Supabase 失敗：", error.message)
  } else {
    console.log("貼文已成功儲存到 Supabase", data)
  }
}

// Elements
const loadDataBtn = document.getElementById('loadDataBtn')
const output = document.getElementById('output')

// Fetch data function
async function loadData() {
  output.textContent = 'Loading...'

  const { data, error } = await supabase
    .from('test_table')      // <-- change this to your table name
    .select('*')

  if (error) {
    output.textContent = 'Error: ' + error.message
  } else {
    output.textContent = JSON.stringify(data, null, 2)
  }
}

// Event listener
loadDataBtn.addEventListener('click', loadData)
