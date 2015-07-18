#ifndef __POCKETFEATURE_C_C__
#define __POCKETFEATURE_C_C__

#ifndef ABS
#define ABS(X) (X < 0 ? -X : X)
#endif

float feature_vector_std_dev_tanimoto(const float *cutoffsVector, 
                                      const float *vectorA, 
                                      const float *vectorB, 
                                      int numFeatures);

void feature_vectors_std_dev_tanimoto(const float *cutoffsVector, 
                                      const float **vectorA, 
                                      const float **vectorB,
                                      int numVectorsA, 
                                      int numVectorsB,
                                      int numFeatures,
                                      float *scores);

#endif
