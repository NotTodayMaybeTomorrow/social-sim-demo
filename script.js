// Supabase configuration - only used if Supabase is available
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk';

let supabaseClient = null;

// Initialize Supabase client only if the library is available
async function initializeSupabase() {
  try {
    if (typeof window.supabase !== 'undefined') {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      console.log('Supabase initialized successfully');
    } else {
      console.log('Supabase library not available - running in demo mode');
    }
  } catch (error) {
    console.log('Supabase initialization failed - running in demo mode:', error);
  }
}

async function submitPost() {
  try {
    const subreddit = "r/" + (document.getElementById("subredditInput").value || "society_sim");
    const title = document.getElementById("title").value;
    const content = document.getElementById("content").value;
    const submissionFlair = document.getElementById("submissionFlair").value;
    const usernameFlair = document.getElementById("usernameFlair").value;
    const isNSFW = document.getElementById("isNSFW").checked;

    // Update post content on the page
    document.getElementById("displayTitle").innerText = title;
    
    // Construct the meta string with styled flairs and new line layout
    let metaText = '<div class="post-meta">';
    
    // First line: Posted by with username flair
    metaText += '<span class="post-meta-line">Posted by u/username';
    if (usernameFlair) {
      metaText += ` <span class="username-flair">${usernameFlair}</span>`;
    }
    metaText += '</span>';
    
    // Second line: Submission flair and NSFW tag (if present)
    if (submissionFlair || isNSFW) {
      metaText += '<span class="post-meta-line">';
      if (submissionFlair) {
        metaText += `<span class="submission-flair">${submissionFlair}</span>`;
      }
      if (isNSFW) {
        metaText += '<span class="nsfw-tag">🔞 NSFW</span>';
      }
      metaText += '</span>';
    }
    
    metaText += '</div>';

    document.getElementById("displayMeta").innerHTML = `<em>${metaText}</em>`;
    document.getElementById("displayContent").innerText = content;
    
    // The comments section is added here after submission
    const commentsHeader = document.getElementById("commentsHeader");
    const commentsList = document.getElementById("commentsList");

    commentsHeader.innerText = "Comments";
    
    const comments = [
      "Wow, really interesting take!",
      "I'm not sure I agree with this, but it's a good post.",
      "This is exactly what I needed to read today."
    ];

    // Clear previous comments and add new ones
    commentsList.innerHTML = comments.slice(0, 3).map(c => `<li>${c}</li>`).join("");

    // The score will be updated after the "simulation"
    const simulatedScore = Math.floor(Math.random() * 200) - 100;
    
    // Update the score on the page
    document.getElementById("displayScore").innerText = simulatedScore;

    // Show the simulation result section
    document.getElementById("simulationResult").style.display = 'block';

    // Try to save to Supabase if available
    if (supabaseClient) {
      try {
        const { data, error } = await supabaseClient
          .from('submissions')
          .insert([{
            subreddit,
            title,
            content,
            username_flair: usernameFlair || null,
            submission_flair: submissionFlair || null,
            is_nsfw: !!isNSFW,
            created_at: new Date().toISOString()
          }]) 
          .select();

        if (error) {
          console.error("Insert failed:", error);
        } else {
          console.log("Insert succeeded:", data);
        }
      } catch (dbError) {
        console.error("Database operation failed:", dbError);
      }
    } else {
      console.log("Post created in demo mode (not saved to database)");
    }

  } catch (error) {
    console.error("Error submitting post:", error);
    alert("There was an error submitting your post. Please try again.");
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize Supabase first
  await initializeSupabase();

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
    if (!supabaseClient) {
      output.textContent = 'Demo mode - no database connection available';
      return;
    }

    output.textContent = 'Loading...';
    try {
      const { data, error } = await supabaseClient.from('submissions').select('*');
      if (error) {
        output.textContent = 'Error: ' + error.message;
      } else {
        output.textContent = JSON.stringify(data, null, 2);
      }
    } catch (error) {
      output.textContent = 'Error loading data: ' + error.message;
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