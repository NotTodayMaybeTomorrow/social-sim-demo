import fs from 'fs';
import snoowrap from 'snoowrap';
import { createClient } from '@supabase/supabase-js';
import * as tf from '@tensorflow/tfjs-node';
import { UniversalSentenceEncoder } from '@tensorflow-models/universal-sentence-encoder';

// Import configuration - you'll need to create a config.js file
import {
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
} from './config.js';

// Supabase setup
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Reddit API setup
const reddit = new snoowrap({
    userAgent: REDDIT_USER_AGENT,
    clientId: REDDIT_CLIENT_ID,
    clientSecret: REDDIT_CLIENT_SECRET,
    refreshToken: undefined, // For read-only access
    accessToken: undefined,
});

// Universal Sentence Encoder model (will be loaded asynchronously)
let model = null;

/**
 * Load the Universal Sentence Encoder model
 */
async function loadModel() {
    if (!model) {
        console.log('Loading Universal Sentence Encoder model...');
        model = await UniversalSentenceEncoder.load();
        console.log('Model loaded successfully!');
    }
    return model;
}

/**
 * Calculate cosine similarity between two vectors
 */
function cosineSimilarity(vecA, vecB) {
    const dotProduct = tf.sum(tf.mul(vecA, vecB));
    const normA = tf.norm(vecA);
    const normB = tf.norm(vecB);
    return tf.div(dotProduct, tf.mul(normA, normB));
}

/**
 * Get the most recent submission from Supabase
 */
async function getLatestSubmission() {
    try {
        const { data, error } = await supabase
            .from('submissions')
            .select('subreddit, submission_flair, is_nsfw, title, content')
            .order('id', { ascending: false })
            .limit(1);

        if (error) {
            console.error('Supabase error:', error);
            return null;
        }

        return data && data.length > 0 ? data[0] : null;
    } catch (error) {
        console.error('Error fetching latest submission:', error);
        return null;
    }
}

/**
 * Test if Reddit API credentials are working
 */
async function testRedditConnection() {
    try {
        const subreddit = reddit.getSubreddit('python');
        await subreddit.getHot({ limit: 1 });
        console.log('Reddit connection test: Connection succeeded.');
        return true;
    } catch (error) {
        console.error('Reddit connection failed:', error);
        return false;
    }
}

/**
 * Fetch posts from Reddit with filtering
 */
async function fetchRedditPosts(subredditName, submissionFlair = null, isNsfw = false, limit = 100) {
    const cleanSubredditName = subredditName.replace('r/', '');
    
    try {
        const subreddit = reddit.getSubreddit(cleanSubredditName);
        const submissions = await subreddit.getHot({ limit: limit });
        
        const posts = [];
        
        for (const submission of submissions) {
            // Filter NSFW
            if (submission.over_18 !== isNsfw) {
                continue;
            }
            
            // Filter flair if specified
            if (submissionFlair && submission.link_flair_text !== submissionFlair) {
                continue;
            }
            
            posts.push({
                title: submission.title,
                content: submission.selftext || submission.title,
                url: submission.url,
                score: submission.score,
                flair: submission.link_flair_text,
                nsfw: submission.over_18,
                id: submission.id,
            });
        }
        
        return posts;
    } catch (error) {
        console.error('Error fetching Reddit posts:', error);
        return [];
    }
}

/**
 * Find most similar posts using Universal Sentence Encoder embeddings + cosine similarity
 */
async function findSimilarPostsEmbeddings(targetPost, redditPosts, topK = 10) {
    if (!redditPosts || redditPosts.length === 0) {
        return [];
    }
    
    const encoder = await loadModel();
    
    const targetText = `${targetPost.title} ${targetPost.content}`;
    const redditTexts = redditPosts.map(post => `${post.title} ${post.content}`);
    
    // Encode with Universal Sentence Encoder
    const targetEmbedding = await encoder.embed([targetText]);
    const redditEmbeddings = await encoder.embed(redditTexts);
    
    // Calculate similarities
    const similarities = [];
    const targetVec = targetEmbedding.arraySync()[0];
    const redditVecs = redditEmbeddings.arraySync();
    
    for (let i = 0; i < redditVecs.length; i++) {
        const targetTensor = tf.tensor1d(targetVec);
        const redditTensor = tf.tensor1d(redditVecs[i]);
        const similarity = await cosineSimilarity(targetTensor, redditTensor);
        similarities.push(await similarity.data());
        
        // Clean up tensors
        targetTensor.dispose();
        redditTensor.dispose();
    }
    
    // Clean up embeddings
    targetEmbedding.dispose();
    redditEmbeddings.dispose();
    
    // Get top k indices
    const indexedSimilarities = similarities.map((sim, idx) => ({ sim: sim[0], idx }));
    indexedSimilarities.sort((a, b) => b.sim - a.sim);
    const topIndices = indexedSimilarities.slice(0, topK);
    
    const similarPosts = [];
    for (const { sim, idx } of topIndices) {
        const post = { ...redditPosts[idx] };
        post.similarity_score = sim;
        similarPosts.push(post);
    }
    
    return similarPosts;
}

/**
 * Main function to collect and structure all the data
 */
async function collectData() {
    // Test Reddit connection
    if (!(await testRedditConnection())) {
        console.log('Please check your Reddit API credentials');
        return null;
    }
    
    // Get latest submission
    const latestSubmission = await getLatestSubmission();
    if (!latestSubmission) {
        console.log('No submissions found in database');
        return null;
    }
    
    console.log(`Latest submission: ${latestSubmission.title}`);
    console.log(`Subreddit: ${latestSubmission.subreddit}`);
    console.log(`Flair: ${latestSubmission.submission_flair}`);
    console.log(`NSFW: ${latestSubmission.is_nsfw}`);
    console.log('-'.repeat(50));
    
    // Fetch Reddit posts
    const redditPosts = await fetchRedditPosts(
        latestSubmission.subreddit,
        latestSubmission.submission_flair,
        latestSubmission.is_nsfw,
        200
    );
    
    console.log(`Found ${redditPosts.length} matching Reddit posts`);
    
    if (redditPosts.length === 0) {
        console.log('No matching posts found on Reddit');
        return null;
    }
    
    // Find similar posts
    const similarPosts = await findSimilarPostsEmbeddings(latestSubmission, redditPosts, 10);
    
    console.log('\nTop 10 most similar posts (using Universal Sentence Encoder):');
    console.log('='.repeat(50));
    
    const finalData = [];
    
    for (let i = 0; i < similarPosts.length; i++) {
        const post = similarPosts[i];
        console.log(`${i + 1}. Title: ${post.title}...`);
        console.log(`   Score: ${post.score} | Similarity: ${post.similarity_score.toFixed(3)}`);
        console.log(`   Flair: ${post.flair} | NSFW: ${post.nsfw}`);
        console.log(`   URL: ${post.url}`);
        console.log('-'.repeat(40));
        
        const postData = { ...post };
        postData.top_level_comments = [];
        
        try {
            const submission = reddit.getSubmission(post.id);
            await submission.expandReplies({ limit: 10, depth: 1 });
            
            const comments = submission.comments.slice(0, 10);
            
            for (const comment of comments) {
                if (postData.top_level_comments.length >= 10) {
                    break;
                }
                
                if (comment.body && comment.body !== '[deleted]' && comment.body !== '[removed]') {
                    const commentData = {
                        score: comment.score,
                        body: comment.body,
                        author: comment.author ? comment.author.name : '[deleted]',
                        author_hot_comments: []
                    };
                    
                    if (comment.author && comment.author.name !== '[deleted]') {
                        try {
                            const authorComments = await comment.author.getComments({ sort: 'hot', limit: 10 });
                            
                            for (const authComment of authorComments) {
                                if (authComment.body && authComment.body !== '[deleted]' && authComment.body !== '[removed]') {
                                    commentData.author_hot_comments.push({
                                        score: authComment.score,
                                        body: authComment.body
                                    });
                                }
                            }
                        } catch (error) {
                            console.log(`   Error fetching comments for ${comment.author.name}: ${error.message}`);
                        }
                    }
                    
                    postData.top_level_comments.push(commentData);
                }
            }
        } catch (error) {
            console.log(`   Error fetching comments for post ${post.id}: ${error.message}`);
        }
        
        finalData.push(postData);
    }
    
    console.log('\nAll data has been saved to the finalData array.');
    return finalData;
}

// Main execution
async function main() {
    try {
        const finalData = await collectData();
        if (finalData) {
            fs.writeFileSync('reddit_data.json', JSON.stringify(finalData, null, 2));
            console.log('Data successfully written to reddit_data.json');
        }
    } catch (error) {
        console.error('Error in main execution:', error);
    } finally {
        // Clean up TensorFlow resources
        if (model) {
            model.dispose();
        }
    }
}

// Run if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}

export { collectData, getLatestSubmission, fetchRedditPosts, findSimilarPostsEmbeddings };