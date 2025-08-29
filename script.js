// Replace these with your actual Supabase project URL and anon key
const SUPABASE_URL = 'https://wfwrdegsjjqlxskvnlgb.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk';

// Initialize Supabase client
import { createClient } from 'https://esm.sh/@supabase/supabase-js';
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Global variables to track state
let currentSubmissionId = null;
let lastCommentsCount = 0;
let subscription = null; // To hold the Supabase subscription
let subscriptionStartTime = null; // To track when the subscription started

const SUBSCRIPTION_DURATION = 60 * 60 * 1000; // 1 hour in milliseconds

// Function to update comments display
async function updateCommentsDisplay() {
  const commentsHeader = document.getElementById("commentsHeader");
  const commentsList = document.getElementById("commentsList");

  // If there's no current submission, ensure any existing subscription is ended
  if (!currentSubmissionId) {
    commentsHeader.innerText = "Comments";
    commentsList.innerHTML = "";
    if (subscription) {
      subscription.unsubscribe();
      subscription = null;
      subscriptionStartTime = null;
      console.log("Subscription to comments ended because currentSubmissionId is null.");
    }
    return;
  }

  // Check if subscription already exists and is still active within the duration
  if (subscription) {
    if (Date.now() - subscriptionStartTime < SUBSCRIPTION_DURATION) {
      console.log("Subscription already active for this submission and within time limit.");
      return; // Already subscribed and within the time limit
    } else {
      // Unsubscribe if the duration has passed
      console.log("Subscription to comments timed out, unsubscribing.");
      subscription.unsubscribe();
      subscription = null;
      subscriptionStartTime = null;
    }
  }

  // Start a new subscription
  console.log(`Subscribing to comments for submission_id: ${currentSubmissionId}`);
  subscriptionStartTime = Date.now(); // Record the start time

  try {
    // SET THE RLS SETTING!
    const { error: rpcError } = await supabaseClient.rpc('set_config', {
        key: 'app.current_submission_id',
        value: String(currentSubmissionId) // Ensure it's a string
    });

    if (rpcError) {
        console.error("Error setting RLS config:", rpcError);
        commentsList.innerHTML = `<li style="color: red;">Failed to set RLS config: ${rpcError.message}</li>`;
        return; // Don't proceed if we can't set the RLS config
    } else {
        console.log("Successfully set RLS config for submission_id:", currentSubmissionId);
    }


    // Fetch initial comments
    const { data: initialComments, error: initialCommentsError } = await supabaseClient
      .from('comments')
      .select('author, content, created_at')
      .eq('submission_id', currentSubmissionId)
      .order('created_at', { ascending: true });

    if (initialCommentsError) {
      console.error("Error loading initial comments:", initialCommentsError);
      commentsList.innerHTML = `<li style="color: red;">Failed to load comments: ${initialCommentsError.message}</li>`;
    } else {
      commentsList.innerHTML = initialComments
        .map((c, index) => `
          <li class="comment-item" data-index="${index}">
            <strong>${c.author || 'Anonymous'}:</strong> ${c.content}
            <span class="comment-time">${new Date(c.created_at).toLocaleTimeString()}</span>
          </li>
        `)
        .join("");

      commentsHeader.innerText = `Comments (${initialComments?.length ?? 0})`;
      lastCommentsCount = initialComments?.length ?? 0;
    }

    // Set up the real-time subscription
    subscription = supabaseClient
      .channel(`comments_subscription_${currentSubmissionId}`) // Use a unique channel name
      .on('postgres_changes', {
        event: '*', // Listen to all events (INSERT, UPDATE, DELETE)
        schema: 'public', // Specify your schema
        filter: `submission_id=eq.${currentSubmissionId}` // Filter for the current submission
      }, (payload) => {
        console.log('Realtime change received:', payload);

        // Handle INSERT event for new comments
        if (payload.eventType === 'INSERT') {
          const newComment = payload.new;
          const newCommentElement = document.createElement('li');
          newCommentElement.classList.add('comment-item');
          newCommentElement.innerHTML = `
            <strong>${newComment.author || 'Anonymous'}:</strong> ${newComment.content}
            <span class="comment-time">${new Date(newComment.created_at).toLocaleTimeString()}</span>
          `;
          commentsList.appendChild(newCommentElement);

          // Update header and count
          const currentCount = commentsList.children.length;
          commentsHeader.innerText = `Comments (${currentCount})`;
          lastCommentsCount = currentCount;

          // Visual feedback for new comments
          commentsList.style.opacity = '0.7';
          setTimeout(() => {
            commentsList.style.opacity = '1';
          }, 200);
        }

        // Check if the subscription should continue after any real-time event
        if (Date.now() - subscriptionStartTime >= SUBSCRIPTION_DURATION) {
          if (subscription) {
            console.log("Subscription to comments timed out, unsubscribing.");
            subscription.unsubscribe();
            subscription = null;
            subscriptionStartTime = null;
          }
        }
      })
      .subscribe((status) => {
        console.log(`Subscription status: ${status}`);
        if (status === 'CHANNEL_ERROR' || status === 'CLOSED') {
          // Handle connection errors or unexpected closures
          console.error(`Subscription error or closed for submission ${currentSubmissionId}`);
          if (subscription) {
            subscription.unsubscribe();
            subscription = null;
            subscriptionStartTime = null;
          }
        }
      });

  } catch (error) {
    console.error("Error setting up comments subscription:", error);
    // Ensure the subscription is cleaned up if an error occurs during setup
    if (subscription) {
      subscription.unsubscribe();
      subscription = null;
      subscriptionStartTime = null;
    }
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
  const simulatedScore = 0; // Start at 0 for new posts
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

      // Load initial comments for this submission and start listening
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

  // Check if all elements exist before proceeding
  if (!subredditInput || !titleInput || !contentInput || !submitBtn || !titleCounter || !contentCounter || !darkModeToggle) {
    console.error('One or more DOM elements not found:', {
      subredditInput: !!subredditInput,
      titleInput: !!titleInput,
      contentInput: !!contentInput,
      submitBtn: !!submitBtn,
      titleCounter: !!titleCounter,
      contentCounter: !!contentCounter,
      darkModeToggle: !!darkModeToggle
    });
    return;
  }

  // Function to update character counters
  function updateCounter(inputElement, counterElement, maxLength) {
    const currentLength = inputElement.value.length;
    counterElement.textContent = `${currentLength}/${maxLength}`;
  }

  // Enable/disable submit button based on required fields
  function validateForm() {
    const subredditValue = subredditInput.value.trim();
    const titleValue = titleInput.value.trim();
    const contentValue = contentInput.value.trim();

    const allFilled = subredditValue !== '' &&
                      titleValue !== '' &&
                      contentValue !== '';

    console.log('Validation check:', {
      subreddit: subredditValue,
      title: titleValue,
      content: contentValue,
      allFilled: allFilled
    });

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

  // Clean up subscriptions when the page is about to unload
  window.addEventListener('beforeunload', () => {
    if (subscription) {
      console.log("Unsubscribing from comments on page unload.");
      subscription.unsubscribe();
    }
  });
});