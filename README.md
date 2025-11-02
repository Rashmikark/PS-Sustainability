# PS-Sustainability
Week 1
Problem Statement - "Machine learning image classification model using 9 physicochemical parameters to predict water potability, enabling rapid field testing for underserved Indian communities."
DEFINITION OF MY PROBLEM STATEMENT:

In many villages, people worry every day about whether their water is safe to drink. 
Testing the water costs ₹500 to ₹2000, which is more than what many families earn in a day. 
Even after paying so much, the results take 3 to 7 days to come. 
The nearest lab is often far away, sometimes more than 50 kilometers.
So, most people simply can’t get their water tested.
Parents do their best — they boil the water, they hope it’s safe — but deep down, they are always worried.
They shouldn’t have to guess if the water they give their children will make them sick.

PROPOSED SOLUTION:
We’re building an AI tool that works like a water safety expert in your pocket — simple, fast, and made for everyone.
It tests 9 key water parameters using a small portable kit and gives an instant answer — “Safe to Drink” or “Unsafe – Don’t Drink.”
No confusing numbers, no waiting for days. Just "click a single image", and in under 5 seconds, you’ll know if your water is safe.
It doesn’t need a lab or a technician - can use it easily. 
It’s almost as reliable as expert testing and works anywhere, bringing peace of mind to families who just want safe water for their loved ones.

DATASET DESCRIPTION:
Source: Kaggle Water Quality and Potability Dataset (2024)
Total Samples: 3,276 water quality measurements
Features (9 parameters):
1. pH: Acidity/alkalinity measure (0-14 scale)
2. Hardness: Mineral content (mg/L)
3. Solids: Total Dissolved Solids - TDS (mg/L)
4. Chloramines: Disinfectant level (mg/L)
5. Sulfate: Sulfur compound concentration (mg/L)
6. Conductivity: Electrical conductivity (μS/cm)
7. Organic_carbon: Organic matter content (mg/L)
8. Trihalomethanes: Disinfection byproducts (μg/L)
9. Turbidity: Cloudiness measure (NTU)

Target Variable: Potability (0 = Not Safe, 1 = Safe)

Data Split: 70% Train | 15% Validation | 15% Test

