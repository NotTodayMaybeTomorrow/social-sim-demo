// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk';

// Initialize Supabase client
import { createClient } from 'https://esm.sh/@supabase/supabase-js';
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Global variables to track state
let currentSubmissionId = null;
let lastCommentsCount = 0;

// Function to update comments display
async function updateCommentsDisplay() {
  const commentsHeader = document.getElementById("commentsHeader");
  const commentsList = document.getElementById("commentsList");
  
  if (!currentSubmissionId) {
    commentsHeader.innerText = "Comments";
    commentsList.innerHTML = "";
    return;
  }

  try {
    const { data: comments, error: commentsError } = await supabaseClient
      .from('comments')
      .select('author, content, created_at')
      .eq('submission_id', currentSubmissionId)
      .order('created_at', { ascending: true });

    if (commentsError) {
      console.error("Error loading comments:", commentsError);
      commentsList.innerHTML = `<li style="color: red;">Failed to load comments: ${commentsError.message}</li>`;
    } else {
      // Check if comments count has changed
      if (comments.length !== lastCommentsCount) {
        console.log(`Comments updated: ${lastCommentsCount} → ${comments.length}`);
        lastCommentsCount = comments.length;
        
        // Add visual feedback for new comments
        if (comments.length > 0) {
          commentsList.style.opacity = '0.7';
          setTimeout(() => {
            commentsList.style.opacity = '1';
          }, 200);
        }
      }

      commentsList.innerHTML = comments
        .map((c, index) => `
          <li class="comment-item" data-index="${index}">
            <strong>${c.author || 'Anonymous'}:</strong> ${c.content}
            <span class="comment-time">${new Date(c.created_at).toLocaleTimeString()}</span>
          </li>
        `)
        .join("");
      
      commentsHeader.innerText = `Comments (${comments?.length ?? 0})`;
    }
  } catch (error) {
    console.error("Error updating comments:", error);
  }
}



async function submitPost() {
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

  // The score will be updated after the "simulation"
  const simulatedScore = Math.floor(Math.random() * 200) - 100;
  document.getElementById("displayScore").innerText = simulatedScore;

  try {
    // Insert the new submission and get the returned data
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
      return;
    }

    console.log("Insert succeeded:", data);
    
    // Set the current submission ID to the newly created submission
    if (data && data.length > 0) {
      currentSubmissionId = data[0].id;
      console.log("Current submission ID set to:", currentSubmissionId);
      
      // Reset comments count
      lastCommentsCount = 0;
      
      // Load initial comments for this submission
      await updateCommentsDisplay();
    }

  } catch (error) {
    console.error("Error submitting post:", error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const subredditInput = document.getElementById("subredditInput");
  const titleInput = document.getElementById("title");
  const contentInput = document.getElementById("content");
  const submitBtn = document.getElementById("submitBtn");
  const titleCounter = document.getElementById("title-counter");
  const contentCounter = document.getElementById("content-counter");
  const darkModeToggle = document.getElementById('darkModeToggle');

  // Set up event listeners

  // Function to update character counters
  function updateCounter(inputElement, counterElement, maxLength) {
    const currentLength = inputElement.value.length;
    counterElement.textContent = `${currentLength}/${maxLength}`;
  }

  // Enable/disable submit button based on required fields
  function validateForm() {
    const allFilled = subredditInput.value.trim() !== '' &&
                      titleInput.value.trim() !== '' &&
                      contentInput.value.trim() !== '';
    submitBtn.disabled = !allFilled;
  }

  // Event listeners
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

  // Clean up when page is about to unload
  window.addEventListener('beforeunload', () => {
    // No cleanup needed since we removed polling
  });
});