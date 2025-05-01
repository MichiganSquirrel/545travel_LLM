# Enhancing Travel Planning with LLMs and Machine Learning Systems

**Team Members:** Yikun Ding, Mingyang Liu, Zhenyu Wang, Xiangpeng Huang, Jiaxi Liang

## Table of Contents
- [Introduction and Objective](#introduction-and-objective)
- [Travel Planner System](#travel-planner-system)
  - [System Design](#system-design)
  - [LLM-Powered Flight Recommendation](#llm-powered-flight-recommendation)
  - [Day-by-Day Travel Planning](#day-by-day-travel-planning)
  - [User Preference Data Pipeline](#user-preference-data-pipeline)
- [Recommendation System](#recommendation-system)
  - [Destination Recommendation Based on User Preferences](#destination-recommendation-based-on-user-preferences)
  - [Predicting User Preferences Based on Destination](#predicting-user-preferences-based-on-destination)
  - [Integration into Travel Agent Workflow](#integration-into-travel-agent-workflow)
- [Summary](#summary)
- [References](#references)

## Introduction and Objective

Modern travelers face significant challenges when planning trips: information overload across countless platforms, difficulty finding truly personalized options, and the time-consuming nature of creating comprehensive itineraries. Our project addresses these challenges through an innovative travel planning and recommendation system that combines machine learning techniques with an intuitive user interface.

Our solution consists of two integrated components working in harmony:

- **Travel Planner System:** An interactive web interface that leverages Large Language Models (LLMs) to process and analyze flight offers and Points of Interest (POI) data from various APIs, transforming raw information into personalized travel recommendations.
    
- **Recommendation System:** A bidirectional framework with dual functionality that:
  - Recommends destinations based on explicit user preferences
  - Predicts user preference characteristics based on chosen destinations, enabling personalized itinerary creation even when users provide minimal input

This bidirectional approach creates a continuous feedback loop that enhances personalization over time, allowing our system to serve both users who know their preferences but need destination suggestions and those who know their destination but need personalized activity recommendations.

Our recommendation system employs two distinct filtering approaches to accommodate different usage scenarios:

- **User-Based Filtering:** Identifies travelers with similar preferences and recommends destinations based on their established travel patterns, particularly effective for returning users with interaction history.
    
- **Content-Based Filtering:** Analyzes the relationship between destination attributes and user preference vectors to suggest compatible locations, especially valuable for new users without prior system interaction.

By integrating these components, we've created a comprehensive travel planning solution that significantly reduces the complexity of trip organization while delivering highly personalized travel experiences tailored to each user's unique preferences and constraints, regardless of their entry point into the system.

## Travel Planner System

### System Design

![Program Structure and User Journey](figure5.png)

We have developed a fully functional, interactive travel planning web interface that serves as the central hub for user interaction. This interface has been carefully designed to balance functionality with ease of use, ensuring that users of varying technical abilities can navigate the system effectively. The frontend features an intuitive layout that guides users step by step through the travel planning process, from initial destination selection to detailed daily itinerary creation.

Behind this user-friendly interface lies a sophisticated backend architecture that supports dynamic itinerary generation. This backend integrates with multiple external APIs to gather comprehensive travel data, including flight search services, lodging options, and activity recommendation platforms. The system also features a custom pipeline that connects to our user preference database, allowing for the continuous refinement of recommendations based on both explicit user inputs and implicit preference signals.

The true strength of our system lies in its ability to tailor travel experiences by considering multiple dimensions of user preferences. These include not only stated preferences such as budget constraints and accommodation requirements but also trip goals, travel history, and destination-specific considerations. By analyzing these multifaceted inputs, our system can generate highly personalized travel suggestions that go beyond the capabilities of conventional booking platforms.

### LLM-Powered Flight Recommendation

A significant innovation in our system is the integration of LLM-powered flight option analysis. Traditional flight recommendation systems typically rely on rigid rule-based algorithms that sort options based on predefined criteria such as price or duration. Our approach fundamentally transforms this process by leveraging the contextual understanding capabilities of large language models.

The workflow begins with gathering raw data from flight APIs, we utilize LLM prompts to automatically organize and summarize the information. This approach offers remarkable flexibility, as the LLM can interpret and prioritize different aspects of flight options based on the specific context of each user's request.

A key strength of our system is its ability to clearly present trade-offs between different flight options. Rather than simply ranking flights based on a single criterion, our system provides explanations of why certain options might be preferable depending on the user's specific needs and constraints. This transparency empowers users to make truly informed decisions, enhancing the overall booking experience and user satisfaction.

To ensure reliable and up-to-date flight information, we integrate with the Amadeus Flight Offers API, which provides real-time access to flight availability, pricing, and details across numerous airlines and routes worldwide.

### Day-by-Day Travel Planning

The day-by-day travel planning component of our system transforms the often overwhelming task of organizing activities at a destination into a streamlined, personalized experience. This functionality integrates two powerful technologies to deliver highly relevant recommendations.

First, we use the OpenAI API to summarize user preference, the preference data comes from both explicit user selections within our interface and insights from our recommendation system, which continuously learns from user interactions. The language model's ability to understand natural language descriptions and contextual nuances allows it to interpret complex preferences that might be difficult to capture in traditional recommendation algorithms.

Second, we retrieve accurate and comprehensive information about Points of Interest (POIs) at the user's destination. These include hotels, landmarks, restaurants, and other attractions that might be relevant to the traveler's interests. The API provides rich details about each location, which serve as the foundation for our recommendation system. Once we have both the user preference data and POI information, our system generates a personalized daily travel plan.

A critical innovation in our approach is the implementation of a supervision model that ensures the integrity of recommendations. This model verifies that all suggested activities and points of interest are grounded in the actual data returned by the Google API, effectively preventing the problem of hallucination (where the LLM might invent fictitious attractions). This verification process maintains the reliability of our recommendations while still allowing for creative and personalized itinerary creation.

Our system also prioritizes user agency by implementing a feedback mechanism. If users are unsatisfied with any aspect of their generated itinerary, they can provide textual feedback directly through the interface. This feedback is then used to fine-tune the travel plan, allowing for iterative refinement until the itinerary meets the user's expectations. This human-in-the-loop approach ensures that the final travel plan truly reflects the user's preferences and requirements.

### User Preference Data Pipeline

The backend of our system features a data pipeline that enables continuous improvement of recommendations through an iterative process. This persistent data storage creates a valuable preference profile for each user that grows more refined with each interaction. Which is an essential part for our recommendation system.

## Recommendation System

Our recommendation system plays a role in personalizing travel planning for users. The system has two functions: (i) recommending travel destinations based on user preferences and (ii) inferring and constructing user profiles based on the travel destinations input by users. These two mechanisms help the recommendation system form a two-way feedback loop, helping the system better understand user profiles and make targeted recommendations.

### Destination Recommendation Based on User Preferences

We use two methods to recommend travel destinations based on user preferences such as cabin type, hotel preferences, food tastes, and activity interests, namely Content-Based Filtering and User-Based Filtering. These two methods are suitable for different scenarios and should be selected based on the availability of data and the required degree of personalization. We collected data from approximately 2,000 users through Google Forms surveys and supplemented this with synthetically generated profiles to ensure comprehensive coverage across various preference combinations, each of which contains the user's selected destination, cabin type, hotel type, and features for food and activities.

#### Content-Based Filtering

The content-based method hinges on the principle that users with similar preference vectors are likely to enjoy similar destinations. Formally, for a given user characterized by a feature vector x_u ∈ ℝ^d, we seek to find a destination d ∈ D such that d ~ x_u.

The workflow begins with preprocessing, where all input features are standardized using Z-score normalization:

```
x_j^norm = (x_j - μ_j) / σ_j
```

Following normalization, we apply K-Means clustering on the user feature matrix X ∈ ℝ^(n×d), where each row corresponds to a user's profile. We determine the optimal number of clusters k = 4 using both the elbow method (which minimizes within-cluster sum of squares) and silhouette scores (which maximize inter-cluster separation):

```
S(i) = (b(i) - a(i)) / max{b(i), a(i)}
```

Once clusters are assigned, we train a cluster-specific XGBoost classifier f_k : ℝ^d → D for each group, where the classifier maps user features to a destination prediction. In deployment, a new user is first assigned to the nearest cluster, and then the corresponding classifier is used to predict the most compatible destination.

![3D PCA Visualization of Clusters](figure1.png)

Figure 2 shows a three-dimensional PCA projection of user preference clusters, where color and spatial separation illustrate the distinct preference patterns learned through K-Means clustering.

This method is especially suitable for new users (cold start) due to its independence from historical behavior data. Visualization of cluster profiles further reveals that our model captures diverse preferences—for instance, Cluster 1 corresponds to users interested in nightlife and shopping (frequenting Los Angeles), while Cluster 3 captures those with strong cultural interests (favoring destinations like New York or Washington, D.C.). Our content-based approach is aligned with the broader methodology described by Lops et al. (2011).

![XGBoost Accuracy by Cluster](figure2.png)

As depicted in Figure 3, XGBoost classifiers trained on different clusters achieve varying accuracy levels, with Cluster 1 exhibiting the highest performance due to its cohesive user preference profile.

#### User-Based Filtering

Unlike the content-based approach, the user-based filtering method assumes that similar users have similar destination preferences. Each user's historical behavior is summarized by an average feature vector x̄_u computed across all their travel records D_u:

```
x̄_u = (1/|D_u|) ∑_(i∈D_u) x_i
```

For a target user u, we compute the Euclidean distance to every other user v in the dataset:

```
dist(u,v) = ||x̄_u - x̄_v||_2
```

Let v* denote the nearest neighbor. We search v*'s travel history to find the record j ∈ D_{v*} such that x_j is closest to x̄_u, and recommend the associated destination d_j.

This approach is particularly effective when a user has multiple prior interactions with the system, as the aggregated vector captures evolving tastes. Additionally, it supports exploratory recommendations by identifying similar users with slight preference deviations, thereby offering novelty without sacrificing relevance. Our user-based filtering method follows principles similar to those discussed by Herlocker et al. (2002).

![User-Based Filtering Recommendation Examples](figure3.png)

Figure 4 displays sample outputs from the user-based filtering approach, showing how different users are matched to recommended destinations based on similarity to their nearest historical neighbors.

### Predicting User Preferences Based on Destination

The second part of our system addresses the inverse problem: predicting a user's latent preferences when only the destination is known. This is useful in scenarios where the user only inputs a travel location, but expects a customized itinerary.

We model this using a destination-cluster-activity pipeline, proceeding as follows. Compute the destination-cluster mapping by estimating the empirical probability P(C = c | d) for each destination d, determining how likely each destination belongs to each cluster. Within each cluster, we then train Random Forest binary classifiers f_{c,i}(d,c) → [0,1] to predict the probability that a user selecting destination d will enjoy activity i (e.g., cultural, outdoors). Finally, predictions for each activity are computed as a weighted average across cluster-specific outputs:

```
ŷ_i = ∑_(c=1)^K P(C=c | d) · f_{c,i}(d,c)
```

![Destination-Cluster-Activity Prediction Outputs](figure4.png)

Figure 5 summarizes the predicted probabilities of various activity interests for each destination, providing a basis for generating personalized and context-sensitive travel itineraries.

This mechanism allows the system to infer user interests accurately and tailor itineraries accordingly. For instance, if a user selects destination 6 (e.g., New York), the model might predict a strong interest in cultural and nightlife activities, leading to tailored recommendations such as museums, shows, and vibrant evening venues. This destination-based inference approach is conceptually similar to methods surveyed by Zhang et al. (2019).

### Integration into Travel Agent Workflow

Destination recommendations and user preference predictions are used in different scenarios, complementing each other and helping our travel recommendation system to better provide personalized customization solutions. For new users, if they provide preferences, the system will provide destination recommendations to users through content based filtering to deal with the cold start problem. If they are old users, user based filtering will be used to recommend destinations to users. If the user only enters the travel destination, the system will infer their profile and then recommend attractions that users with similar profiles like.

## Summary

To equip our travel planning system with more robustness, integrating the following APIs could further improve the accuracy and personalization of our program:

- Incorporate **weather APIs** to tailor activity based on real-time weather conditions.
- Add **local event APIs** to recommend festivals or seasonal activities.

Regarding our user profiling and clustering recommendation analysis, although we incorporated a generated test dataset for sheer analysis purposes without access to corporate user information backends, the clustering approach demonstrates the potential to segment real-world users based on their idiosyncratic travel behaviors and preferences. This method can be scaled and applied to actual user data to provide meaningful insights and deliver personalized recommendations or potential promotions. 

Our proposed approach also enhances user privacy, as it does not collect nor rely on sensitive personal information such as income, gender, or age group. Instead, our study's main focus is solely on travel behaviors and preferences.

## References

1. Herlocker, J. L., Konstan, J. A., & Riedl, J. (2002). An empirical analysis of design choices in neighborhood-based collaborative filtering algorithms. *Information Retrieval*, 5(4), 287–310. https://doi.org/10.1023/A:1020443909834
    
2. Lops, P., de Gemmis, M., & Semeraro, G. (2011). Content-based recommender systems: State of the art and trends. In F. Ricci, L. Rokach, B. Shapira, & P. B. Kantor (Eds.), *Recommender Systems Handbook* (pp. 73–105). Springer. https://doi.org/10.1007/978-0-387-85820-3_3
    
3. Zhang, S., Yao, L., Sun, A., & Tay, Y. (2019). Deep learning based recommender system: A survey and new perspectives. *ACM Computing Surveys*, 52(1), 1–38. https://doi.org/10.1145/3285029

4. Jian Xie, Kai Zhang, Jiangjie Chen, Tinghui Zhu, Renze Lou, Yuandong Tian, Yanghua Xiao, Yu Su. TravelPlanner: A Benchmark for Real-World Planning with Language Agents. 2024. arXiv, https://arxiv.org/abs/2402.01622

5. Kurniawan Eka Permana, Abdullah Basuki Rahmat, Eka Mala Sari Rochman, Aery Rachmad, Sigit Susanto Putro. Tourism Recommendation System Using Collaborative User-Based Filtering. 2025. https://doi.org/10.1063/5.0241251
