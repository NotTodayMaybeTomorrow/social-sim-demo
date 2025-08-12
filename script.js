// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk'

// Initialize Supabase client
const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

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
