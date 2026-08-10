#!/usr/bin/env node

/**
 * Token Reduction Benchmark for GLM Code Graph
 * Uses tiktoken (OpenAI tokenizer) via Node.js
 */

const fs = require('fs');
const path = require('path');

// Load tiktoken (OpenAI's tokenizer)
const { encoding_for_model } = require('tiktoken');

// Initialize tokenizer (GLM-4 uses similar tokenizer)
const ENCODING = encoding_for_model('gpt-4');

function countTokens(content) {
    return ENCODING.encode(content).length;
}

function getFileSize(filePath) {
    const stats = fs.statSync(filePath);
    return stats.size;
}

function main() {
    console.log('\n' + '='.repeat(70));
    console.log(' '.repeat(15) + 'TOKEN REDUCTION VERIFICATION');
    console.log('='.repeat(70));

    const repoPath = path.join(__dirname);

    // Get all Python files (exclude tests for clean review)
    let allFiles = [];
    const pyFiles = fs.readdirSync(repoPath, { recursive: true });
    
    pyFiles.forEach(file => {
        const fullPath = path.join(repoPath, file);
        const stat = fs.statSync(fullPath);
        
        if (stat.isFile() && file.endsWith('.py')) {
            // Skip test files and __pycache__
            if (!file.startsWith('test_') && !file.includes('__pycache__')) {
                allFiles.push(fullPath);
            }
        }
    });

    // Sort files
    allFiles.sort();

    console.log('\n[1] Total files in codebase:');
    allFiles.forEach((file, i) => {
        const size = getFileSize(file);
        console.log(`    ${i + 1}. ${path.basename(file).padEnd(20)} ${size.toString().padStart(6)} bytes`);
    });

    // Calculate total
    const totalSize = allFiles.reduce((sum, f) => sum + getFileSize(f), 0);
    console.log(`\n[2] Total size: ${totalSize.toLocaleString()} bytes`);

    // Read all content (traditional approach)
    console.log('\n[3] Reading all files for traditional review...');
    let allContent = '';
    allFiles.forEach(file => {
        const content = fs.readFileSync(file, 'utf8');
        allContent += content + '\n';
    });

    const allTokens = countTokens(allContent);
    console.log(`    Total tokens: ${allTokens.toLocaleString()}`);
    console.log(`    Size: ${allContent.length.toLocaleString()} bytes`);

    // BLAST RADIUS ANALYSIS
    console.log('\n' + '='.repeat(70));
    console.log(' '.repeat(18) + 'BLAST RADIUS ANALYSIS');
    console.log('='.repeat(70));

    // Review auth.py
    const reviewFile = 'auth.py';
    console.log(`\n[4] Reviewing changed file: ${reviewFile}`);

    const reviewPath = path.join(repoPath, reviewFile);
    let blastFiles = [reviewPath];

    // Parse imports
    const reviewContent = fs.readFileSync(reviewPath, 'utf8');
    const importLines = [];
    
    const lines = reviewContent.split('\n');
    lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
            importLines.push(trimmed);
        }
    });

    console.log(`\n    Import statements in ${reviewFile}:`);
    importLines.forEach(imp => console.log(`      - ${imp}`));

    // Extract modules and add to blast radius
    importLines.forEach(imp => {
        let module;
        if (imp.includes('import ')) {
            module = imp.split('import ')[1].split('.')[0].trim();
        } else {
            module = imp.split('from ')[1].split(' import ')[0].trim();
        }

        const modulePath = path.join(repoPath, `${module}.py`);
        if (fs.existsSync(modulePath) && !module.startsWith('test_')) {
            blastFiles.push(modulePath);
            console.log(`    → Adding import: ${module}.py`);
        }
    });

    // Find test files
    const testFiles = allFiles.filter(f => f.includes('test_'));
    if (testFiles.length > 0) {
        console.log(`\n    Test files: ${testFiles.length} file(s)`);
        blastFiles = blastFiles.concat(testFiles);
    }

    console.log(`\n[6] Blast radius files (${blastFiles.length} total):`);
    blastFiles.forEach((file, i) => {
        const size = getFileSize(file);
        console.log(`    ${i + 1}. ${path.basename(file).padEnd(20)} ${size.toString().padStart(6)} bytes`);
    });

    // Calculate blast radius content
    console.log('\n[7] Reading blast radius files...');
    let blastContent = '';
    blastFiles.forEach(file => {
        const content = fs.readFileSync(file, 'utf8');
        blastContent += content + '\n';
    });

    const blastTokens = countTokens(blastContent);
    const blastSize = blastContent.length;

    console.log(`    Total tokens: ${blastTokens.toLocaleString()}`);
    console.log(`    Size: ${blastSize.toLocaleString()} bytes`);

    // Comparison
    console.log('\n' + '='.repeat(70));
    console.log(' '.repeat(15) + 'COMPARISON RESULTS');
    console.log('='.repeat(70));

    const filesSaved = allFiles.length - blastFiles.length;
    const sizeReduction = ((totalSize - blastSize) / totalSize) * 100;
    const tokenReduction = ((allTokens - blastTokens) / allTokens) * 100;

    console.log(`\n[8] Traditional Review:`);
    console.log(`    Files read:   ${allFiles.length}`);
    console.log(`    Content size: ${totalSize.toLocaleString()} bytes`);
    console.log(`    Tokens:       ${allTokens.toLocaleString()}`);

    console.log(`\n[9] GLM Code Graph (Blast Radius):`);
    console.log(`    Files read:   ${blastFiles.length}`);
    console.log(`                    (${filesSaved} files saved)`);
    console.log(`    Content size: ${blastSize.toLocaleString()} bytes`);
    console.log(`    Tokens:       ${blastTokens.toLocaleString()}`);

    console.log(`\n[10] Reduction Metrics:`);
    console.log(`    Files:   ${filesSaved} (${(filesSaved/allFiles.length*100).toFixed(1)}% saved)`);
    console.log(`    Size:    ${sizeReduction.toFixed(1)}% smaller`);
    console.log(`    Tokens:  ${tokenReduction.toFixed(1)}% fewer`);

    // Cost calculation (estimated)
    const costPerToken = 0.00001; // $0.00001 per token for GLM-4
    const reviewCost = blastTokens * costPerToken;
    const savedCost = (allTokens - blastTokens) * costPerToken;
    const monthlySavings = savedCost * 100; // Assuming 100 reviews/month

    console.log(`\n[11] Expected Cost Savings:`);
    console.log(`    • Review cost: $${reviewCost.toFixed(4)}`);
    console.log(`    • Saved: $${savedCost.toFixed(4)}`);
    console.log(`    • Monthly savings (100 reviews): ~$${monthlySavings.toFixed(2)}`);

    console.log('\n' + '='.repeat(70));
    console.log(' '.repeat(20) + 'CONCLUSION');
    console.log('='.repeat(70));
    console.log(`\n✓ GLM Code Graph achieves ${tokenReduction.toFixed(1)}% token reduction`);
    console.log(`✓ ${filesSaved} files skipped per review`);
    console.log(`✓ Significant cost savings on frequent code reviews`);
    console.log();
}

main();
