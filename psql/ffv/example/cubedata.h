/* derived from contrib/cube/cubedata.h */

/* TODO: Make this as large as the largest possible FEATURE Vector */
#define FFV_MAX_SHELLS (15)
#define FFV_MAX_PROPERTIES (127)
#define FFV_MAX_DIM (FFV_MAX_SHELLS * FFV_MAX_PROPERTIES)


typedef struct NDBOX
{
	/* varlena header (do not touch directly!) */
	int32		vl_len_;

	/*----------
	 * Header contains info about NDBOX. For binary compatibility with old
	 * versions, it is defined as "unsigned int".
	 *
	 * Following information is stored:
	 *
	 *	bits 0-3   : number of shells;
	 #  bits 4-10  : number of properties;
	 *	bits 11-30 : unused, initialize to zero;
	 *	bit  31    : normalized flag. If set, vector is understood to be a Z-score
	                 instead of a raw feature vector
	 *----------
	 */
	unsigned int header;

	/*
	 * Variable length array. The lower left coordinates for each dimension
	 * come first, followed by upper right coordinates unless the point flag
	 * is set.
	 */
	double		x[1];
} NDBOX;

#define Z_BIT			    0x80000000
#define SHELL_MASK			0x0000000F
#define PROPERTY_MASK   	0x00000FF0
#define DATA_MASK           SHELL_MASK | PROPERTY_MASK

#define DEFAULT_FFV_FLAG    80 << 4 + 6
#define DEFAULT_FFV_SIZE    480

#define IS_Z_SCORE(ffv)		        ( ((ffv)->header & Z_BIT) != 0 )
#define SET_Z_BIT(ffv)              ( (ffv)->header |= Z_BIT )
#define SIZE_FLAG(ffv)		        ( (ffv)->header & DATA_MASK )
#define N_SHELLS(ffv)               ( (ffv)->header & SHELL_MASK )
#define N_PROPS(ffv)                ( ( (ffv)->header & PROPERTY_MASK ) >> 4 )
#define SIZE(ffv)                   ( ( (ffv)->header == DEFAULT_FFV_FLAG ) ? DEFAULT_FFV_SIZE : ( N_SHELLS(ffv) * N_PROPS(ffv) ) )
#define SET_N_SHELLS(ffv, _shells)  ( (ffv)->header = ((ffv)->header & ~SHELL_MASK) | (_shells) )
#define SET_N_PROPS(ffv, _props)    ( (ffv)->header = ((ffv)->header & ~PROPERTY_MASK) | ((_props) << 4) )
#define SET_DIM(cube, _dim) ( (cube)->header = ((cube)->header & ~DIM_MASK) | (_dim) )

#define LL_COORD(cube, i) ( (cube)->x[i] )
#define UR_COORD(cube, i) ( IS_POINT(cube) ? (cube)->x[i] : (cube)->x[(i) + DIM(cube)] )

#define POINT_SIZE(_dim) (offsetof(NDBOX, x[0]) + sizeof(double)*(_dim))
#define CUBE_SIZE(_dim) (offsetof(NDBOX, x[0]) + sizeof(double)*(_dim)*2)

#define DatumGetNDBOX(x)	((NDBOX*)DatumGetPointer(x))
#define PG_GETARG_NDBOX(x)	DatumGetNDBOX( PG_DETOAST_DATUM(PG_GETARG_DATUM(x)) )
#define PG_RETURN_NDBOX(x)	PG_RETURN_POINTER(x)
