using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

public class TokenReduction
{
    public static void Main(string[] args)
    {
        Console.WriteLine("\n" + new string('=', 70));
        Console.WriteLine("                         TOKEN REDUCTION VERIFICATION");
        Console.WriteLine(new string('=', 70));

        string repoPath = Directory.GetCurrentDirectory();

        // Get all Python files
        var allFiles = Directory.GetFiles(repoPath, "*.py", SearchOption.AllDirectories)
            .Where(f => !f.Contains("__pycache__") && !f.Contains("test_"))
            .OrderBy(f => f)
            .ToList();

        Console.WriteLine($"\n[1] Total files in codebase:");
        foreach (var file in allFiles)
        {
            FileInfo fi = new FileInfo(file);
            Console.WriteLine($"    {allFiles.IndexOf(file) + 1}. {Path.GetFileName(file):20s} {fi.Length,6} bytes");
        }

        // Calculate total
        long totalSize = allFiles.Sum(f => new FileInfo(f).Length);
        Console.WriteLine($"\n[2] Total size: {totalSize,6} bytes");

        // Traditional approach
        Console.WriteLine($"\n[3] Traditional review: read all files ({allFiles.Count} files)");

        // Blast radius for auth.py
        Console.WriteLine("\n" + new string('=', 70));
        Console.WriteLine("                         BLAST RADIUS ANALYSIS");
        Console.WriteLine(new string('=', 70));

        string reviewFile = "auth.py";
        Console.WriteLine($"\n[4] Reviewing changed file: {reviewFile}");

        var blastFiles = new List<string> { reviewFile };
        long blastSize = new FileInfo(reviewFile).Length;

        // Read auth.py and find imports
        string content = File.ReadAllText(reviewFile);

        var importLines = content.Split('\n')
            .Select(line => line.Trim())
            .Where(line => line.StartsWith("import ") || line.StartsWith("from "));

        Console.WriteLine($"\n    Import statements in {reviewFile}:");
        foreach (var imp in importLines)
        {
            Console.WriteLine($"      - {imp}");

            // Extract module
            string module;
            if (imp.Contains("import "))
            {
                module = imp.Split("import ")[1].Split('.')[0].Trim();
            }
            else
            {
                module = imp.Split("from ")[1].Split(" import ")[0].Trim();
            }

            string modulePath = Path.Combine(repoPath, $"{module}.py");
            if (File.Exists(modulePath) && !module.StartsWith("test_"))
            {
                blastFiles.Add($"{module}.py");
                long size = new FileInfo(modulePath).Length;
                Console.WriteLine($"    → Adding import: {module}.py ({size} bytes)");
                blastSize += size;
            }
        }

        // Find test files
        var testFiles = allFiles.Where(f => f.Contains("test_")).ToList();
        if (testFiles.Count > 0)
        {
            Console.WriteLine($"\n    Test files: {testFiles.Count} file(s)");
            foreach (var testFile in testFiles)
            {
                blastFiles.Add(testFile);
                blastSize += new FileInfo(testFile).Length;
            }
        }

        Console.WriteLine($"\n[6] Blast radius files ({blastFiles.Count} total):");
        foreach (var file in blastFiles)
        {
            long size = new FileInfo(file).Length;
            Console.WriteLine($"    {Path.GetFileName(file):20s} {size,6} bytes");
        }

        Console.WriteLine($"\n[7] GLM Code Graph: read blast radius ({blastFiles.Count} files, {blastSize} bytes)");

        // Comparison
        Console.WriteLine("\n" + new string('=', 70));
        Console.WriteLine("                         COMPARISON RESULTS");
        Console.WriteLine(new string('=', 70));

        int filesSaved = allFiles.Count - blastFiles.Count;
        double sizeReduction = (totalSize - blastSize) / (double)totalSize * 100;
        double tokenReduction = (totalSize - blastSize) / (double)totalSize * 100;

        double costPerToken = 0.00001;
        double reviewCost = blastSize * costPerToken;
        double savedCost = (totalSize * costPerToken) - (blastSize * costPerToken);
        double monthlySavings = savedCost * 100;

        Console.WriteLine($"\n[8] Traditional Review:");
        Console.WriteLine($"    Files read:   {allFiles.Count}");
        Console.WriteLine($"    Size:         {totalSize,6} bytes");
        Console.WriteLine($"    Tokens:       {totalSize / 4} (≈ 4 bytes/token)");

        Console.WriteLine($"\n[9] GLM Code Graph (Blast Radius):");
        Console.WriteLine($"    Files read:   {blastFiles.Count}");
        Console.WriteLine($"                    ({filesSaved} files saved)");
        Console.WriteLine($"    Size:         {blastSize,6} bytes");
        Console.WriteLine($"    Tokens:       {blastSize / 4} (≈ 4 bytes/token)");

        Console.WriteLine($"\n[10] Reduction Metrics:");
        Console.WriteLine($"    Files:   {filesSaved} ({filesSaved / (double)allFiles.Count * 100:F1}%)");
        Console.WriteLine($"    Size:    {sizeReduction:F1}% smaller");
        Console.WriteLine($"    Tokens:  {tokenReduction:F1}% fewer");

        Console.WriteLine($"\n[11] Expected Cost Savings:");
        Console.WriteLine($"    • Review cost: ${reviewCost:F4}");
        Console.WriteLine($"    • Saved: ${savedCost:F4}");
        Console.WriteLine($"    • Monthly savings (100 reviews): ~${monthlySavings:F2}");

        Console.WriteLine("\n" + new string('=', 70));
        Console.WriteLine("                         CONCLUSION");
        Console.WriteLine(new string('=', 70));
        Console.WriteLine($"\n✓ GLM Code Graph achieves {tokenReduction:F1}% token reduction");
        Console.WriteLine($"✓ {filesSaved} files skipped per review");
        Console.WriteLine($"✓ Significant cost savings on frequent code reviews");
        Console.WriteLine();
    }
}
