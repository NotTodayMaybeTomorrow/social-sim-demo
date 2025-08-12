// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://your-project-ref.supabase.co'
const SUPABASE_ANON_KEY = 'your-anon-key'

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
