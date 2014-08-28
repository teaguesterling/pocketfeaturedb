#include <math.h>
#include "feature_tanimoto.h"


float feature_vector_std_dev_tanimoto(const float *cutoffsVector, 
                                      const float *vectorA, 
                                      const float *vectorB, 
                                      int numFeatures) {
    int i;          // Counter
    float a, b;     // Vector values
    int n_share,    // Shared feature 
        n_total;    // Total features present
    n_share = n_total = 0;

    for(i = 0; i < len; i++) {
        a = vectorA[i];
        b = vectorB[i];
        if(a != 0 || b !=0) {
            n_total++;
            if(abs(a - b) <  cutoffsVector[i]) {
                n_share++;
            }
        }
    }
    return ((float) n_shared) / n_total;
}

float feature_vector_std_dev_compare(const float *cutoffsVector, 
                                     const float *vectorA, 
                                     const float *vectorB, 
                                     int numFeatures) {
    int i;          // Counter
    float a, b;     // Vector values
    int n_share,    // Shared feature 
        n_total;    // Total features present
    n_share = n_total = 0;

    for(i = 0; i < len; i++) {
        a = vectorA[i];
        b = vectorB[i];
        if(a != 0 || b !=0) {
            n_total++;
            if(abs(a - b) <  cutoffsVector[i]) {
                n_share++;
            }
        }
    }
    return ((float) n_shared) / (2 * n_total - n_shared);
}

void feature_vectors_std_dev_tanimoto(const float *cutoffsVector, 
                                      const float **vectorA, 
                                      const float **vectorB,
                                      int numVectorsA, 
                                      int numVectorsB,
                                      int numFeatures,
                                      float *scores) {
    int i, j, s;
    for(i = 0; i < numVectorsA; i++) {
        for(j = 0; j < numVectorsB; j++) {
            s = i * numVectorsA + j;
            scores[s] = feature_vector_std_dev_tanimoto(cutoffsVector,
                                                        vectorA[i],
                                                        vectorB[j],
                                                        numFeatures);
        }
    }
}

void feature_vectors_std_dev_compare(const float *cutoffsVector, 
                                     const float **vectorA, 
                                     const float **vectorB,
                                     int numVectorsA, 
                                     int numVectorsB,
                                     int numFeatures,
                                     float *scores) {
    int i, j, s;
    for(i = 0; i < numVectorsA; i++) {
        for(j = 0; j < numVectorsB; j++) {
            s = i * numVectorsA + j;
            scores[s] = feature_vector_std_dev_compare(cutoffsVector,
                                                       vectorA[i],
                                                       vectorB[j],
                                                       numFeatures);
        }
    }
}

