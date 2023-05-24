/* eslint-disable react/jsx-no-comment-textnodes */
/*
 * Copyright 2022 Agnostiq Inc.
 * Note: This file is subject to a proprietary license agreement entered into between
 * you (or the person or organization that you represent) and Agnostiq Inc. Your rights to
 * access and use this file is subject to the terms and conditions of such agreement.
 * Please ensure you carefully review such agreements and, if you have any questions
 * please reach out to Agnostiq at: [support@agnostiq.com].
 */

import { Button, Grid, Typography, SvgIcon } from '@mui/material'
import React from 'react'
import { ReactComponent as ViewSvg } from '../../assets/qelectron/view.svg'
import { ReactComponent as QelectronSvg } from '../../assets/qelectron/qelectron.svg'

const QElectronCard = (props) => {
  const { qElectronDetails, toggleQelectron, openQelectronDrawer } = props

  const handleButtonClick = (event) => {
    event.stopPropagation()
    toggleQelectron()
  }
  return (
    //main container
    <Grid
      onClick={handleButtonClick}
      conatiner
      mt={5}
      p={2}
      sx={{
        background: 'transparent',
        border: '1px solid',
        borderRadius: '8px',
        cursor: 'pointer',
        borderColor: (theme) => theme.palette.primary.grey,
        '&:hover': {
          backgroundColor: (theme) => theme.palette.background.default,
        },
      }}
    >
      <Grid
        item
        xs={12}
        container
        direction="row"
        alignItems="center"
        justifyContent="space-between"
      >
        <Grid item container xs={6} direction="row" alignItems="center">
          <Typography sx={{ fontSize: '16px', mr: 1 }}>
            {qElectronDetails.title}
          </Typography>
          <span style={{ flex: 'none' }}>
            <SvgIcon
              aria-label="view"
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                mr: 0,
                mt: 0.8,
                pr: 0,
              }}
            >
              <QelectronSvg />
            </SvgIcon>
          </span>
        </Grid>
        <Button
          sx={{
            textTransform: 'capitalize',
            height: '2rem',
            width: '4.5rem',
            backgroundColor: (theme) => theme.palette.primary.blue02,
            color: (theme) => theme.palette.text.primary,
            '&:hover': {
              backgroundColor: (theme) => theme.palette.primary.blue02,
            },
          }}
        >
          <span style={{ flex: 'none' }}>
            <SvgIcon
              aria-label="view"
              sx={{
                display: 'flex',
                justifyContent: 'flex-end',
                mr: 0,
                mt: 1.1,
                pr: 0,
              }}
            >
              <ViewSvg />
            </SvgIcon>
          </span>
          <span style={{ flex: 'none', pl: 0, ml: 0, fontSize: '12px' }}>
            {!openQelectronDrawer ? 'Open' : 'Close'}
          </span>
        </Button>
      </Grid>
      <Grid
        item
        xs={12}
        mt={3}
        container
        direction="row"
        alignItems="center"
        justifyContent="space-between"
      >
        <Grid item sx={{ display: 'flex', flexDirection: 'column' }}>
          <Typography sx={{ fontSize: '12px' }}>Quantum Calls</Typography>
          <Typography sx={{ fontSize: '14px' }}>
            {qElectronDetails.quantam_calls}
          </Typography>
        </Grid>
        <Grid item sx={{ display: 'flex', flexDirection: 'column' }}>
          <Typography sx={{ fontSize: '12px' }}>Avg Time Of Call</Typography>
          <Typography sx={{ fontSize: '14px' }}>
            {qElectronDetails.avg_time_ofcall}
          </Typography>
        </Grid>
      </Grid>
    </Grid>
  )
}

export default QElectronCard
